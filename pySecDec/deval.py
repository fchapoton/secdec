#!/usr/bin/env python3
"""
Distributed pySecDec integral evaluator.
Usage: python3 -m pySecDec.deval integrand.json [--points=N] [--epsrel=N] [--shifts=N] param=value ...
"""

import asyncio
import base64
import collections
import json
import numpy as np
import os
import pickle
import re
import subprocess
import sympy as sp
import sys
import time

from .generating_vectors import generating_vector

log_starttime = time.time()
def log(*args):
    print(f"{time.time() - log_starttime:.3f}]", *args)
    sys.stdout.flush()

# Generic RPC

def encode_payload(data):
    return base64.b64encode(pickle.dumps(data))

def decode_payload(binary):
    return pickle.loads(base64.b64decode(binary))

class Worker:

    def __init__(self, process, name=None):
        self.name = name
        self.process = process
        self.serial = 0
        self.callbacks = {}
        self.callback_args = {}
        self.reader_task = asyncio.get_event_loop().create_task(self._reader())

    def call_cb(self, method, args, callback, callback_args=()):
        i = self.serial = self.serial + 1
        self.callbacks[i] = callback
        self.callback_args[i] = callback_args
        data = encode_payload({"m": method, "a": args, "i": i})
        message = b"@call " + data + b"\n"
        self.process.stdin.write(message)

    def call(self, method, *args):
        fut = asyncio.futures.Future()
        def call_return(result, error):
            if error is None: fut.set_result(result)
            else: fut.set_exception(error)
        self.call_cb(method, args, call_return)
        fut.par_worker = self
        fut.par_method = method
        fut.par_args = args
        return fut

    async def _reader(self):
        log(f"{self.name}: started reading")
        rx = re.compile(b"^@([a-zA-Z0-9_]+)(?: ([^\\n]*))?\n$")
        try:
            while True:
                line = await self.process.stdout.readline()
                if len(line) == 0: break
                m = rx.match(line)
                if m is not None:
                    cmd, arg = m.groups()
                    if cmd == b"return":
                        arg = decode_payload(arg)
                        callback = self.callbacks[arg["i"]]
                        callback_args = self.callback_args[arg["i"]]
                        del self.callbacks[arg["i"]]
                        del self.callback_args[arg["i"]]
                        callback(arg.get("r"), arg.get("e"), *callback_args)
                    else:
                        log(f"{self.name}: {line}")
                else:
                    log(f"{self.name}: {line}")
        except Exception as e:
            log(f"{self.name} reader failed: {type(e).__name__}: {e}")
        log(f"{self.name} reader exited")

async def launch_worker(command, maxtimeout=10):
    timeout = min(1, maxtimeout/10)
    while True:
        log(f"starting {command}")
        p = await asyncio.create_subprocess_shell(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        p.stdin.write(b"@start\n")
        answer = await p.stdout.readline()
        if answer.startswith(b"@started "):
            name = answer[9:].strip().decode("utf-8")
            w = Worker(p, name=name)
            log(f"worker {w.name} connected")
            return w
        else:
            log(f"failed to start worker: {answer}")
            try:
                p.stdin.close()
                p.kill()
            except ProcessLookupError:
                pass
            log(f"will retry after {timeout}s")
            time.sleep(timeout)
            timeout = min(timeout*2, maxtimeout)

# Job scheduling

Job_Integrate = collections.namedtuple("Job_Integrate",
    "future iname kname dim lattice index1 index2 genvec shift realp complexp deformp complex_result")

class Scheduler:
    def __init__(self):
        self.workers = []
        self.sent = []
        self.todo = []
        self.starttimes = {}
        self.C_average = 100.0
        self.C_by_family = {}
        self.C_by_kernel = {}
        self.todo_updated = asyncio.Event()

    def integrate(self, iname, kname, dim, lattice, genvec, shift, realp, complexp, deformp, complex_result):
        fut = asyncio.futures.Future()
        self.todo.append(Job_Integrate(
            fut, iname, kname, dim, lattice, 0, lattice, genvec, shift, realp, complexp, deformp, complex_result))
        self.todo_updated.set()
        return fut

    def job_complexity(self, job):
        c = self.C_by_kernel.get((job.iname, job.kname), None)
        if c is not None: return c
        c = self.C_by_family.get(job.iname, None)
        if c is not None: return c
        return self.C_average

    def job_time_estimate(self, job, worker):
        return self.job_complexity(job)*(job.index2 - job.index1)/worker.speed + worker.overhead

    def schedule(self, end_dt):
        if len(self.todo) == 0: return
        now = time.time()
        end = now + end_dt
        log(f"-- scheduling {len(self.todo)} jobs --")
        self.todo.sort(key=lambda j: self.job_complexity(j)*(j.index2 - j.index1), reverse=True)
        endtimes = {w.name:max(0, self.starttimes.get(w.name, now)) for w in self.workers}
        qsizes = {w.name:0 for w in self.workers}
        for w, j in self.sent:
            endtimes[w.name] += self.job_time_estimate(j, w)
            qsizes[w.name] += 1
        log("queue end time estimates:")
        for wname, t in endtimes.items():
            log(f"- {wname}: {qsizes[wname]} items, {t-now:.3f}s")
        while len(self.todo) > 0:
            w = min(self.workers, key=lambda w: endtimes[w.name])
            if endtimes[w.name] > end:
                log(f"min endtime is now {endtimes[w.name]-now}")
                break
            j = self.todo.pop()
            endtimes[w.name] += self.job_time_estimate(j, w)
            qsizes[w.name] += 1
            #log(f"scheduling on {w.name} till {endtimes[w.name]-now:.3f}: {j.iname}.{j.kname} {j.index2-j.index1:.2e}p {self.job_time_estimate(j, w):.2e}s")
            self.sent.append((w, j))
            w.call_cb("integrate", (j.iname, j.kname,
                    j.dim, j.lattice, j.index1, j.index2, j.genvec, j.shift,
                    j.realp, j.complexp, j.deformp, j.complex_result),
                    self._integrate_job_return, (w, j))
        log("queue end estimates (still", len(self.todo), "jobs todo):")
        for wname, t in endtimes.items():
            log(f"- {wname}: {qsizes[wname]} items, {t-now:.3f}s")

    async def schedule_periodically(self):
        timeout = 0.05
        while True:
            try:
                self.schedule(2.0)
            except Exception as e:
                log("SCHEDULER FAIL:", e)
            if len(self.todo) > 0:
                log(f"scheduler: sleeping for {timeout}")
                await asyncio.sleep(timeout)
                timeout = min(0.20, timeout*1.125)
            else:
                log("scheduler: waiting for more work")
                self.todo_updated.clear()
                await self.todo_updated.wait()
                await asyncio.sleep(0.0001)

    def _integrate_job_return(self, result, error, worker, job):
        try:
            value, dn, dt = result
            if not np.isnan(value):
                c = max((dt - worker.int_overhead)*worker.speed/dn, 1.0)
                if (job.iname, job.kname) in self.C_by_kernel:
                    c = 0.75*self.C_by_kernel[job.iname, job.kname] + 0.25*c
                self.C_by_kernel[job.iname, job.kname] = c
                self.C_by_family[job.iname] = np.mean([
                    v for (i, k), v in self.C_by_kernel.items()
                    if i == job.iname
                ])
                self.C_average = np.mean([v for v in self.C_by_family.values()])
            self.sent.remove((worker, job))
            if any(w is worker for w, j in self.sent):
                self.starttimes[worker.name] = time.time() - worker.latency*0.5
            else:
                if worker.name in self.starttimes:
                    del self.starttimes[worker.name]
                log(f"{worker.name} has no work anymore!")
            if error is None: job.future.set_result(value)
            else: job.future.set_exception(error)
        except Exception as e:
            log("INT JOB RET ERR:", e)

# Integration

async def integrate(par, family, kernel, dim, lattice, genvec, nshifts, realp, complexp, deformp, complex_result):
    if isinstance(deformp, int) and deformp > 0:
        deformp = await presample(par, family, kernel, dim, min(lattice//20, 10**4), nshifts,
                realp, complexp, deformp)
    results = np.array(await asyncio.gather(*[
        par.integrate(family, kernel, dim, lattice, genvec, np.random.rand(dim),
            realp, complexp, deformp, complex_result)
        for i in range(nshifts)
    ]))
    if np.iscomplexobj(results):
        var = (np.var(np.real(results)) + (1j)*np.var(np.imag(results)))/nshifts
    else:
        var = np.var(results)/nshifts
    return np.mean(results)/lattice, var/lattice**2

async def presample(par, family, kernel, dim, npoints, nshifts, realp, complexp, deformp_count):
    lattice, genvec = generating_vector(dim, npoints)
    log(f"start presample for {family}.{kernel}, lattice={lattice}, nshifts={nshifts}")
    async def target(lamb):
        result, var = await integrate(par,
                family, kernel, dim, lattice, genvec, nshifts,
                realp, complexp, np.ones(deformp_count)*lamb, True)
        return lamb, None if np.any(np.isnan(result)) else np.abs(var)
    maxlamb = 1.0
    bestloss = np.inf
    bestlamb = 1.0
    todo = set()
    while True:
        if bestloss is np.inf:
            while len(todo) < 5:
                todo.add(target(maxlamb))
                maxlamb *= 0.5
        else:
            if len(todo) == 0:
                break
        done, todo = await asyncio.wait(todo, return_when=asyncio.FIRST_COMPLETED)
        for r in done:
            lamb, loss = await r
            if loss is not None and loss < bestloss:
                bestloss = loss
                bestlamb = lamb
    log(f"optimized {family}.{kernel}: deformp={bestlamb} loss={bestloss}")
    return np.ones(deformp_count)*bestlamb

# Weighted sum integration

WeightedIntegral = collections.namedtuple("WeightedIntegral",
    "iname kname dim realp complexp deformp complex_result")

def abs2(x):
    return np.real(x)**2 + np.imag(x)**2

def adjust_n(W2, V, v, a, tau, n0):
    lam = (1/V * (W2**(1/(a+1)) @ (v * (a*v/tau)**(-a/(a+1)))))**((a+1)/a)
    n = (a*v/tau * np.max((lam * W2.T).T, axis=0))**(1/(a+1))
    # Same as above, but taking into account that we already did
    # n0 points per integral.
    while np.any(n < n0) and np.any(n > n0):
        mask = n > n0
        n[~mask] = n0[~mask]
        VV = V - W2[:,~mask] @ (v[~mask]/n0[~mask]**a)
        VV = np.maximum(VV, np.zeros_like(VV))
        lam = (1/VV * (W2[:,mask]**(1/(a+1)) @ (v[mask] * (a*v[mask]/tau[mask])**(-a/(a+1)))))**((a+1)/a)
        nn = (a*v[mask]/tau[mask] * np.max((lam * W2[:,mask].T).T, axis=0))**(1/(a+1))
        n[mask] = nn
    return n

async def integrate_weighted_sums(par, W, integrals, epsrel, nshifts=32, scaling=2, npoints0=10**5, K=10):
    def int_one(par, wi, lattice, genvec, nshifts):
        return integrate(par, wi.iname, wi.kname, wi.dim, lattice, genvec, nshifts,
                wi.realp, wi.complexp, wi.deformp, wi.complex_result)
    W2 = abs2(W)
    oldlattice = [None] * len(integrals)
    results = [None] * len(integrals)
    lattice, genvec = zip(*[generating_vector(wi.dim, npoints0) for wi in integrals])
    while True:
        newresults = await asyncio.gather(*[
            int_one(par, wi, lattice[i], genvec[i], nshifts)
            for i, wi in enumerate(integrals)
            if lattice[i] != oldlattice[i]
        ])
        j = 0
        for i in range(len(integrals)):
            if lattice[i] != oldlattice[i]:
                if results[i] is None:
                    log(f"int[{i}] = {newresults[j]} @ {lattice[i]}")
                else:
                    oval, oerr = results[i]
                    nval, nerr = newresults[j]
                    k = np.sqrt((np.real(oerr) + np.imag(oerr))/(np.real(nerr) + np.imag(nerr)))
                    p = lattice[i]/oldlattice[i]
                    log(f"int[{i}] = {newresults[j]} @ {lattice[i]} ({k:.2f}x precision at {p:.1f}x lattice)")
                    if k < 1.0:
                        # Unlucky lattice size; replace the result with the old one.
                        newresults[j] = results[i]
                results[i] = newresults[j]
                j += 1
        oldlattice = lattice
        vals = np.array([v for v, e in results])
        errs = np.array([e for v, e in results])
        val = W @ vals
        var = W2 @ errs
        relerr = np.max(np.sqrt((np.real(var) + np.imag(var))/abs2(val)))
        log("val =", val)
        log("relerr =", relerr)
        if relerr < epsrel:
            log("precision reached")
            for i in range(len(integrals)):
                log(f"lattice[{i}] = {lattice[i]}")
            return val, var
        tau = np.array([par.C_by_kernel[wi.iname, wi.kname] for wi in integrals])
        v = np.array([(np.real(errs[i]) + np.imag(errs[i])) * lattice[i]**scaling for i in range(len(integrals))])
        n = adjust_n(W2, abs2(val)*epsrel**2, v, scaling, tau, np.array(lattice))
        n = np.clip(n, lattice, np.array(lattice)*K)
        newlattice, newgenvec = zip(*[
            generating_vector(wi.dim, n[i])
            for i, wi in enumerate(integrals)
        ])
        # Ugh. Do something smarter here.
        assert newlattice != lattice
        for i, (l1, l2) in enumerate(zip(lattice, newlattice)):
            if l1 != l2:
                log(f"lattice[{i}] = {l1} -> {l2} ({l2/l1:.1f}x)")
        lattice, genvec = newlattice, newgenvec

# Main

async def benchmark_worker(w, info):
    lattice, genvec = generating_vector(2, 10**3)
    shift = np.array([0.3, 0.8])
    realp = np.array([2.0, 0.1, 0.2, 0.3])
    deformp = np.array([1.0, 1.0])
    # Measure round-trip latency.
    latency = []
    for i in range(4):
        t0 = time.time()
        await w.call("ping")
        latency.append(time.time() -  t0)
    w.latency = latency = np.mean(latency)
    # Calculate worker's total per-message overhead by how many
    # empty jobs can it do per second.
    t0 = time.time()
    bench0 = await asyncio.gather(*[
        w.call("integrate_gauge", lattice, 0, lattice, genvec, shift, realp, None, deformp)
        for i in range(50)
    ])
    t1 = time.time()
    w.overhead = (t1-t0-latency)/len(bench0)
    # Give the worker a big enough job so that the linear part of
    # the scaling would dominate over the integration overhead.
    # Figure out FLOPS that way.
    dt0 = min(dt for v, dn, dt in bench0)
    w.int_overhead = dt0
    for k in (5,6,7,8,9):
        lattice, genvec = generating_vector(2, 10**k)
        v, dn, dt = await w.call("integrate_gauge",
                lattice, 0, lattice, genvec, shift, realp, None, deformp)
        if dt > dt0*100:
            break
    w.speed = dn/(dt - dt0)

def bracket(expr, varlist):
    """
    Collect terms in the SymPy expression by powers of the
    variables; return a dict. Example:
    >>> bracket(sp.sympify("1 + 2*a + 3*b + 4*a*b"), sp.var(["a", "b"]))
    {(0, 0): 1, (1, 0): 2, (0, 1): 3, (1, 1): 4}
    """
    result = {}
    orders = sp.collect(expr, varlist[0], evaluate=False)
    othervars = varlist[1:]
    for stem, coef in orders.items():
        power = int(stem.exp) if stem.is_Pow else 0 if stem == 1 else 1
        if othervars:
            for powers, c in bracket(coef, othervars).items():
                result[(power,) + powers] = c
        else:
            result[(power,)] = coef
    return result

async def doeval(par, workers, dirname, info, npoints, epsrel, nshifts, realp, complexp):
    t0 = time.time()
    async def add_worker(cmd):
        w = await launch_worker(cmd)
        await w.call("load", os.path.join(dirname, info["name"] + ".json"))
        await benchmark_worker(w, info)
        par.workers.append(w)
    await asyncio.gather(*[add_worker(cmd) for cmd in workers])
    log("workers:")
    for w in par.workers:
        log(f"- {w.name}: int speed={w.speed:.2e}bps, int overhead={w.int_overhead:.2e}s, total overhead={w.overhead:.2e}s, latency={w.latency:.2e}s")
    # Figure out the coefficient matrix between the expansion
    # order and the full kernel list.
    kernels = []
    for o in info["orders"]:
        kernels.extend(o["kernels"])
    kernel2idx = {k : i for i, k in enumerate(kernels)}
    sp_regulators = sp.var(info["regulators"])
    prefactor = bracket(sp.sympify(info["prefactor"]), sp_regulators)
    prefactor = {p : complex(c) for p, c in prefactor.items()}
    orders = {}
    for o in info["orders"]:
        powers = np.array(o["regulator_powers"])
        for pow, coef in prefactor.items():
            p = powers + pow
            c = complex(coef)
            if np.all(p <= info["expansion_orders"]):
                orders.setdefault(tuple(p), np.zeros(len(kernels), dtype=np.complex128))
                for k in o["kernels"]:
                    orders[tuple(p)][kernel2idx[k]] += coef
    W = np.stack([w for p, w in orders.items()])
    t1 = time.time()
    # Presample all kernels
    deformp = await asyncio.gather(*[
        presample(par, info["name"], k, info["dimension"], 10**4, nshifts,
            realp, complexp, info["deformp_count"])
        for k in kernels
    ])
    t2 = time.time()
    # Integrate the weighted sum
    ints = [
        WeightedIntegral(info["name"], k,
            info["dimension"], realp, complexp, defp, info["complex_result"])
        for k, defp in zip(kernels, deformp)
    ]
    value, variance = await integrate_weighted_sums(par, W, ints, epsrel, nshifts=nshifts, npoints0=npoints)
    t3 = time.time()
    log("startup time:", t1-t0)
    log("presampling time:", t2-t1)
    log("integration time:", t3-t2)
    log("result:")
    for p, val, var in sorted(zip(orders.keys(), value, variance)):
        err = np.sqrt(np.real(var)) + (1j)*np.sqrt(np.imag(var))
        stem = " * ".join(f"{r}^{p}" for r, p in zip(sp_regulators, p))
        log(f"{stem} == {val:+.18e}")
        log(f"{stem} +- {err:+.18e} ({np.abs(err)/np.abs(val):.2e})")

def load_cluster_json(dirname):
    try:
        with open(os.path.join(dirname, "pysecdec.cluster.json", "r")) as f:
            return json.load(f)
    except FileNotFoundError:
        pass
    try:
        processes = len(os.sched_getaffinity(0))
    except AttributeError:
        processes = os.cpu_count()
    log(f"Can't find pysecdec.cluster.json; will run locally on {processes} CPUs")
    return {"cluster": [{"count": processes, "command": f"python3 -m pySecDec.dworker --cpu '{dirname}'"}]}

def main():

    if len(sys.argv) < 2:
        print(__doc__.strip())
        exit(1)

    intfile = sys.argv[1]
    dirname = os.path.dirname(intfile)

    valuemap = {}
    npoints = 10**4
    epsrel = 1e-4
    nshifts = 32
    for arg in sys.argv[2:]:
        if "=" not in arg: raise ValueError(f"Bad argument: {arg}")
        key, value = arg.split("=", 1)
        if key == "--points": npoints = int(float(value))
        elif key == "--epsrel": epsrel = float(value)
        elif key == "--shifts": nshifts = int(float(value))
        elif key.startswith("--"): raise ValueError(f"Unknown option: {key}")
        else:
            value = complex(value)
            value = value.real if value.imag == 0 else value
            valuemap[key] = value
            log(f"{key} = {value}")

    with open(intfile, "r") as f:
        info = json.load(f)

    realp = np.array([valuemap[p] for p in info["realp"]], dtype=np.float64)
    complexp = np.array([valuemap[p] for p in info["complexp"]], dtype=np.complex128)

    cluster = load_cluster_json(dirname)

    workers = []
    for w in cluster["cluster"]:
        workers.extend([w["command"]] * w.get("count", 1))

    if len(workers) == 0:
        print("No workers defined in pysecdec.cluster.json.")
        exit(1)

    par = Scheduler()

    loop = asyncio.get_event_loop()
    scheduler = loop.create_task(par.schedule_periodically())
    loop.run_until_complete(doeval(par, workers, dirname, info, npoints, epsrel, nshifts, realp, complexp))
    scheduler.cancel()

if __name__ == "__main__":
    main()
