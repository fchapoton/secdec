#ifndef SecDecUtil_integrator_hpp_included
#define SecDecUtil_integrator_hpp_included

/*
 * This file defines a general integrator interface for real and complex-valued functions.
 *
 * Real integrators only have to implement the function "get_integrate()",
 * which returns a function taking an integrand container and returning an UncorrelatedDeviation.
 *
 * Complex integrators using "IntegrandContainer" have to implement the function "get_together_integrate()"
 * to integrate real and imaginary part at the same time
 * and/or "get_real_integrator()", which should return a unique pointer to a real-valued version of
 * the integrator. The latter can then be used to integrate real and imaginaty part separately
 * if the boolean member variable "together" is set to false.
 *
 * Complex integrators using a generalized "container_t" can override "get_together_integrate()" for
 * integrating the real and imaginary part in one go. For separate real and imaginary integration, such integrators
 * have to implement a custom "integrate" function.
 */

#ifdef SECDEC_WITH_CUDA
    #include <thrust/complex.h>
#endif
#include <complex>
#include <memory>
#include <stdexcept>
#include <secdecutil/integrand_container.hpp>
#include <secdecutil/uncertainties.hpp>

namespace secdecutil
{

  template<typename return_t, typename input_t, typename container_t = secdecutil::IntegrandContainer<return_t, input_t const * const>> // TODO: cuda example
  struct Integrator
  {
  protected:
    virtual std::function<secdecutil::UncorrelatedDeviation<return_t>
      (const container_t&)>
      get_integrate() = 0;

  public:
    const std::function<secdecutil::UncorrelatedDeviation<return_t>
      (const container_t&)>
      integrate;

    Integrator() :
    integrate
    (
      [ this ] (const container_t& integrand_container)
      {
          return get_integrate()(integrand_container);
      }
    ) {};

  virtual ~Integrator() = default;

  };

  #define COMPLEX_INTEGRATOR(complex_template) \
  template<typename return_t, typename input_t> \
  struct Integrator<complex_template<return_t>, input_t> \
  { \
  using container_t = secdecutil::IntegrandContainer<complex_template<return_t>, input_t const * const>; \
 \
  protected: \
    virtual std::unique_ptr<Integrator<return_t, input_t>> get_real_integrator() \
    { \
      throw std::runtime_error("Separate integration of real and imaginary part is not available because pointer to real-valued integrator is not implemented for this integrator. Try \"together = true\"."); \
    } \
 \
    virtual std::function<secdecutil::UncorrelatedDeviation<complex_template<return_t>> \
      (const container_t&)> \
      get_together_integrate() \
    { \
      throw std::runtime_error("Simultaneous integration of real and imaginary part is not implemented for this integrator. Try \"together = false\"."); \
    } \
 \
  public: \
 \
    bool together; \
    const std::function<secdecutil::UncorrelatedDeviation<complex_template<return_t>> (const container_t&)> integrate; \
 \
    Integrator() : \
    together(false), \
    integrate \
    ( \
      [ this ] (const container_t& integrand_container) \
      { \
        if (together) { \
 \
          return get_together_integrate()(integrand_container); \
 \
        } else { \
 \
          auto real_integrator = this->get_real_integrator(); \
          auto real_part = real_integrator->integrate(complex_to_real::real(integrand_container)); \
          auto imag_part = real_integrator->integrate(complex_to_real::imag(integrand_container)); \
          return secdecutil::UncorrelatedDeviation<complex_template<return_t>>({real_part.value,imag_part.value},{real_part.uncertainty,imag_part.uncertainty}); \
 \
        } \
    } \
    ) {}; \
 \
    virtual ~Integrator() = default; \
 \
  };

  COMPLEX_INTEGRATOR(std::complex)
  #ifdef SECDEC_WITH_CUDA
    COMPLEX_INTEGRATOR(thrust::complex)
  #endif
  #undef COMPLEX_INTEGRATOR

  #define COMPLEX_INTEGRATOR(complex_template) \
  template<typename return_t, typename input_t, typename container_t> \
  struct Integrator<complex_template<return_t>, input_t, container_t> \
  { \
  protected: \
    virtual std::function<secdecutil::UncorrelatedDeviation<complex_template<return_t>> \
      (const container_t&)> \
      get_together_integrate() \
    { \
      throw std::runtime_error("Simultaneous integration of real and imaginary part is not implemented for this integrator. Try \"together = false\"."); \
    } \
 \
  public: \
 \
    bool together; \
    const std::function<secdecutil::UncorrelatedDeviation<complex_template<return_t>> (const container_t&)> integrate; \
 \
    Integrator \
    ( \
      const std::function<secdecutil::UncorrelatedDeviation<complex_template<return_t>> (const container_t&)>& integrate \
    ) : \
      together(false), \
      integrate(integrate) \
    {}; \
 \
    Integrator() : \
    together(false), \
    integrate \
    ( \
      [ this ] (const container_t& integrand_container) \
      { \
        if (together) { \
 \
          return get_together_integrate()(integrand_container); \
 \
        } else { \
 \
          throw std::runtime_error("Simultaneous integration of real and imaginary part is not implemented for this integrator. Try \"together = false\"."); \
 \
        } \
      } \
    ) {}; \
 \
    virtual ~Integrator() = default; \
 \
  };

  COMPLEX_INTEGRATOR(std::complex)
  #ifdef SECDEC_WITH_CUDA
    COMPLEX_INTEGRATOR(thrust::complex)
  #endif
  #undef COMPLEX_INTEGRATOR

/*
 * The class "MultiIntegrator" defines an integrator
 * that switches between two integrators depending on
 * the dimension of the integrand: If the integrand
 * is lower dimensional than "critical_dim" then
 * "low_dim_integrator", otherwise "high_dim_integrator"
 * is used.
 */

  template<typename return_t, typename input_t, typename container_t = secdecutil::IntegrandContainer<return_t, input_t const * const>>
  struct MultiIntegrator : Integrator<return_t,input_t,container_t>
  {
    Integrator<return_t,input_t,container_t>& low_dim_integrator;
    Integrator<return_t,input_t,container_t>& high_dim_integrator;
    int critical_dim;

    /* Constructor */
    MultiIntegrator
    (
      Integrator<return_t,input_t,container_t>& low_dim_integrator,
      Integrator<return_t,input_t,container_t>& high_dim_integrator,
      int critical_dim
    ) :
      low_dim_integrator(low_dim_integrator),
      high_dim_integrator(high_dim_integrator),
      critical_dim(critical_dim)
    {};

    std::function<secdecutil::UncorrelatedDeviation<return_t>
      (const container_t&)>
      get_integrate()
      {
        return [this](const container_t& ic)
          {
            if (ic.number_of_integration_variables < critical_dim)
              return low_dim_integrator.integrate(ic);
            else
              return high_dim_integrator.integrate(ic);
          };
      }

  };

  #define COMPLEX_MULTIINTEGRATOR(complex_template) \
  template<typename return_t, typename input_t, typename container_t> \
  struct MultiIntegrator<complex_template<return_t>,input_t,container_t> : Integrator<complex_template<return_t>,input_t,container_t> \
  { \
    Integrator<complex_template<return_t>,input_t,container_t>& low_dim_integrator; \
    Integrator<complex_template<return_t>,input_t,container_t>& high_dim_integrator; \
    int critical_dim; \
 \
    std::function<secdecutil::UncorrelatedDeviation<complex_template<return_t>> \
      (const container_t&)> \
      get_together_integrate() \
      { \
        return [this] (const container_t& ic) \
        { \
          if (ic.number_of_integration_variables < critical_dim) \
            return low_dim_integrator.integrate(ic); \
          else \
            return high_dim_integrator.integrate(ic); \
        }; \
    }; \
 \
    /* Constructor */ \
    MultiIntegrator \
    ( \
      Integrator<complex_template<return_t>,input_t,container_t>& low_dim_integrator, \
      Integrator<complex_template<return_t>,input_t,container_t>& high_dim_integrator, \
      int critical_dim \
    ) : \
      low_dim_integrator(low_dim_integrator), \
      high_dim_integrator(high_dim_integrator), \
      critical_dim(critical_dim) \
    { this->together = true; }; \
 \
  };

  COMPLEX_MULTIINTEGRATOR(std::complex)
  #ifdef SECDEC_WITH_CUDA
    COMPLEX_MULTIINTEGRATOR(thrust::complex)
  #endif
  #undef COMPLEX_MULTIINTEGRATOR

}

#endif
