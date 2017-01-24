"""Unit tests for the Polynomial container class"""

from .geometric import *
from .common import Sector
from ..algebra import Polynomial, ExponentiatedPolynomial, LogOfPolynomial
from ..misc import argsort_2D_array
from nose.plugins.attrib import attr
import numpy as np
import sympy as sp
import sys
import unittest

python_major_version = sys.version[0]

def sort_2D_array(array):
    'Use the .misc.argsort_2D_array function to sort an array'
    return array[argsort_2D_array(array)]

class TestGeomethod(unittest.TestCase):
    def setUp(self):
        self.p0 = Polynomial.from_expression('x0+x1+x0*x1', ['x0','x1'])
        self.p1 = Polynomial.from_expression('1+x0+x1', ['x0','x1'])
        self.target_hull = np.array([[2,1],
                                     [1,2],
                                     [2,0],
                                     [1,0],
                                     [0,2],
                                     [0,1]])
        self.sorted_target_hull = sort_2D_array(self.target_hull)
        self.target_fan_p01 = [[(1,-1),(1,0),(0,1)],
                               [(-1,1),(1,0),(0,1)]]
        self.sorted_target_fan_p01 = sorted([sorted(cone) for cone in self.target_fan_p01])
        self.p2 = Polynomial.from_expression('x0+x0*x2+x1*x2', ['x0','x1','x2'])
        self.target_fan_p2 = [[(1,-1,-1),(1,-1,0),(1,0,0),(0,1,0),(0,0,1)],
                              [(-1,1,1),(1,0,0),(0,1,0),(0,0,1)]]
        self.sorted_target_fan_p2 = sorted([sorted(cone) for cone in self.target_fan_p2])

    #@attr('active')
    def test_Cheng_Wu(self):
        Feynman_parameters = ['x1', 'x2', 'x3']
        x1, x2, x3 = sp.symbols(Feynman_parameters)
        poly_sympy = sp.sympify('x1*x2 + 5*x2*x3')
        other_sympy = sp.sympify('a + x3*6')
        poly = Polynomial.from_expression(poly_sympy, Feynman_parameters)
        other = Polynomial.from_expression(other_sympy, Feynman_parameters)
        sector = Sector([poly], [other])

        primary_x3 = Cheng_Wu(sector)
        # ``x2`` factorizes in ``poly``
        self.assertEqual( (sp.sympify(primary_x3.cast[0].factors[0]) - x2).simplify() , 0 )
        self.assertEqual( (sp.sympify(primary_x3.cast[0].factors[1]) - (poly_sympy/x2).subs('x3',1)).simplify() , 0 )
        self.assertEqual( (sp.sympify(primary_x3.other[0]) - other_sympy.subs('x3',1)).simplify() , 0 )

        primary_x1 = Cheng_Wu(sector,0)
        # ``x2`` factorizes in ``poly``
        self.assertEqual( (sp.sympify(primary_x1.cast[0].factors[0]) - x2).simplify() , 0 )
        self.assertEqual( (sp.sympify(primary_x1.cast[0].factors[1]) - (poly_sympy/x2).subs('x1',1)).simplify() , 0 )
        self.assertEqual( (sp.sympify(primary_x1.other[0]) - other_sympy.subs('x1',1)).simplify() , 0 )

    #@attr('active')
    def test_Cheng_Wu_one_variable(self):
        U = Polynomial([[1]], [  1  ], ['x0'])
        F = Polynomial([[2]], ['msq'], ['x0'])
        initial_sector = Sector([U,F])
        primary_sector = Cheng_Wu(initial_sector)

        target_decomposed_U = sp.sympify(1)
        target_decomposed_F = sp.sympify('msq')

        self.assertEqual(  ( sp.sympify(primary_sector.cast[0]) - target_decomposed_U ).simplify() , 0   )
        self.assertEqual(  ( sp.sympify(primary_sector.cast[1]) - target_decomposed_F ).simplify() , 0   )

    def test_convex_hull(self):
        hull = convex_hull(self.p0, self.p1)

        # The ordering is not important but must be fixed to compare the arrays
        sorted_hull = sort_2D_array(hull)
        np.testing.assert_array_equal(sorted_hull, self.sorted_target_hull)

    def test_generate_fan(self):
        fan_p01 = generate_fan(self.p0,self.p1)
        fan_p2 = generate_fan(self.p2)
        sorted_fan_p01 = sorted([sorted(cone) for cone in fan_p01])
        sorted_fan_p2 = sorted([sorted(cone) for cone in fan_p2])
        np.testing.assert_array_equal(sorted_fan_p01, self.sorted_target_fan_p01)
        np.testing.assert_array_equal(sorted_fan_p2, self.sorted_target_fan_p2)

    #@attr('active')
    def test_convex_hull_exponentiated_polynomial(self):
        p0 = ExponentiatedPolynomial(self.p0.expolist, self.p0.coeffs, polysymbols=self.p0.polysymbols, exponent='8-3*eps')
        p1 = ExponentiatedPolynomial(self.p1.expolist, self.p1.coeffs, polysymbols=self.p1.polysymbols, exponent='1-2*eps')

        hull = convex_hull(p0, p1)

        # The ordering is not important but must be fixed to compare the arrays
        sorted_hull = sort_2D_array(hull)
        np.testing.assert_array_equal(sorted_hull, self.sorted_target_hull)

    #@attr('active')
    def test_triangulate(self):
        # basic consistency checks working?
        simplicial_cone = [[ 1,  0,  0], [ 0,  1,  0], [ 0, -1, -1]]
        self.assertRaisesRegexp(ValueError, 'simplicial.*already', triangulate, simplicial_cone)
        wrong_dimensionality = [ 1,  0,  0]
        self.assertRaisesRegexp(AssertionError, '(M|m)ust.*two.*dim', triangulate, wrong_dimensionality)
        two_rays = [[ 1,  0,  0], [ 0,  1,  0]]
        self.assertRaisesRegexp(AssertionError, '(M|m)ust.*at least.*dim', triangulate, two_rays)


        cone = [[ 1,  0,  0], [ 0,  1,  0], [ 0, -1, -1], [-1,  0, -1]]
        cone_normal = [[ -1, 1, 1], [ 1, 0, 0], [ 0, 1, 0], [ 0, 0, 1]]

        # useful error message?
        self.assertRaisesRegexp(
                                    OSError, 'No such file or directory.*nonexistentNormalizExecutable',
                                    triangulate, cone, normaliz='nonexistentNormalizExecutable',
                                    workdir='tmpdir_test_triangulate_python' + python_major_version
                               )

        triangulated_cones = triangulate(cone, workdir='tmpdir_test_triangulate_python' + python_major_version)
        triangulated_cones_normal = triangulate(cone_normal, workdir='tmpdir_test_triangulate_python' + python_major_version, switch_representation=True)

        # there are two possibilities for the triangualtion
        target_triangulated_cones1 = np.array([
                                                [[ 1,  0,  0], [ 0,  1,  0], [-1,  0, -1]],
                                                [[ 1,  0,  0], [ 0, -1, -1], [-1,  0, -1]]
                                            ])
        target_triangulated_cones2 = np.array([
                                                [[ 0, -1, -1], [ 0,  1,  0], [ 1,  0,  0]],
                                                [[ 0, -1, -1], [ 0,  1,  0], [-1,  0, -1]]
                                            ])
        target_triangulated_cones1_normal = np.array([
                                                [[ 1,  1,  0], [ 1,  0,  1], [ 0,  0, 1]],
                                                [[ 1,  1,  0], [ 0, 1, 0], [0,  0, 1]]
                                            ])
        target_triangulated_cones2_normal = np.array([
                                                [[ 1, 0, 1], [ 0,  1,  0], [ 0,  0,  1]],
                                                [[ 1, 0, 1], [ 0,  1,  0], [ 1,  1, 0]]
                                            ])

        # should get one of these triangulations
        # The ordering is not important but must be fixed to compare the arrays
        try:
            np.testing.assert_array_equal(sort_2D_array(triangulated_cones[0]), sort_2D_array(target_triangulated_cones1[0]))
            np.testing.assert_array_equal(sort_2D_array(triangulated_cones[1]), sort_2D_array(target_triangulated_cones1[1]))
        except AssertionError:
            try:
                np.testing.assert_array_equal(sort_2D_array(triangulated_cones[0]), sort_2D_array(target_triangulated_cones1[1]))
                np.testing.assert_array_equal(sort_2D_array(triangulated_cones[1]), sort_2D_array(target_triangulated_cones1[0]))
            except AssertionError:
                try:
                    np.testing.assert_array_equal(sort_2D_array(triangulated_cones[0]), sort_2D_array(target_triangulated_cones2[0]))
                    np.testing.assert_array_equal(sort_2D_array(triangulated_cones[1]), sort_2D_array(target_triangulated_cones2[1]))
                except:
                    np.testing.assert_array_equal(sort_2D_array(triangulated_cones[0]), sort_2D_array(target_triangulated_cones2[1]))
                    np.testing.assert_array_equal(sort_2D_array(triangulated_cones[1]), sort_2D_array(target_triangulated_cones2[0]))

        try:
            np.testing.assert_array_equal(sort_2D_array(triangulated_cones_normal[0]), sort_2D_array(target_triangulated_cones1_normal[0]))
            np.testing.assert_array_equal(sort_2D_array(triangulated_cones_normal[1]), sort_2D_array(target_triangulated_cones1_normal[1]))
        except AssertionError:
            try:
                np.testing.assert_array_equal(sort_2D_array(triangulated_cones_normal[0]), sort_2D_array(target_triangulated_cones1_normal[1]))
                np.testing.assert_array_equal(sort_2D_array(triangulated_cones_normal[1]), sort_2D_array(target_triangulated_cones1_normal[0]))
            except AssertionError:
                try:
                    np.testing.assert_array_equal(sort_2D_array(triangulated_cones_normal[0]), sort_2D_array(target_triangulated_cones2_normal[0]))
                    np.testing.assert_array_equal(sort_2D_array(triangulated_cones_normal[1]), sort_2D_array(target_triangulated_cones2_normal[1]))
                except:
                    np.testing.assert_array_equal(sort_2D_array(triangulated_cones_normal[0]), sort_2D_array(target_triangulated_cones2_normal[1]))
                    np.testing.assert_array_equal(sort_2D_array(triangulated_cones_normal[1]), sort_2D_array(target_triangulated_cones2_normal[0]))


    #@attr('active')
    def test_transform_variables(self):
        x0 = Polynomial.from_expression('x0',['x0','x1','x2'])
        x1 = Polynomial.from_expression('x1',['x0','x1','x2'])
        x2 = Polynomial.from_expression('x2',['x0','x1','x2'])

        y0 = Polynomial.from_expression('y0',['y0','y1','y2','y3'])
        y1 = Polynomial.from_expression('y1',['y0','y1','y2','y3'])
        y2 = Polynomial.from_expression('y2',['y0','y1','y2','y3'])
        y3 = Polynomial.from_expression('y3',['y0','y1','y2','y3'])

        composite_polynomial = x0 * x0 * x1
        exponentiated_polynomial = ExponentiatedPolynomial([[2,1,0],[0,0,0]], [1,2], polysymbols='x', exponent='exponent')
        log_of_polynomial = LogOfPolynomial([[2,1,0],[0,1,1]], [1,2], polysymbols='x')

        transformation = np.array([[ 0, 0, 0, 1],   # x0 -> y3
                                   [ 1, 1, 0, 0],   # x1 -> y0*y1
                                   [ 1, 1, 1,-2]])  # x2 -> y0*y1*y2*y3**-2

        transformed_x0 = y3
        transformed_x1 = y0 * y1
        transformed_x2 = Polynomial(expolist=[[1, 1, 1,-2]], coeffs=[1], polysymbols='y')
        transformed_composite_polynomial = transformed_x0 * transformed_x0 * transformed_x1
        transformed_exponentiated_polynomial = ExponentiatedPolynomial([[1,1,0,2],[0,0,0,0]], [1,2], polysymbols='y', exponent='exponent')
        transformed_log_of_polynomial = LogOfPolynomial([[1,1,0,2],[2,2,1,-2]], [1,2], polysymbols='y')

        self.assertEqual( ( sp.sympify(transformed_x0) - sp.sympify(transform_variables(x0, transformation)) ).simplify() , 0)
        self.assertEqual( (sp.sympify(transformed_x1) - sp.sympify(transform_variables(x1, transformation))).simplify() , 0)
        self.assertEqual( (sp.sympify(transformed_x2) - sp.sympify(transform_variables(x2, transformation))).simplify() , 0)
        self.assertEqual( (sp.sympify(transformed_composite_polynomial) - sp.sympify(transform_variables(composite_polynomial, transformation))).simplify() , 0)

        self.assertTrue(type(transform_variables(exponentiated_polynomial, transformation)) is ExponentiatedPolynomial)
        self.assertEqual( (sp.sympify(transformed_exponentiated_polynomial) - sp.sympify(transform_variables(exponentiated_polynomial, transformation))).simplify() , 0)

        self.assertTrue(type(transform_variables(log_of_polynomial, transformation)) is LogOfPolynomial)
        self.assertEqual( (sp.sympify(transformed_log_of_polynomial) - sp.sympify(transform_variables(log_of_polynomial, transformation))).simplify() , 0)

    #@attr('active')
    def test_2D_geometric_decomposition(self):
        poly = Polynomial.from_expression('x1 + x2 + x1*x2', ['dummy','x1','x2'])
        sector = Sector([poly])
        indices = [1,2]
        subsectors = list( geometric_decomposition(sector, indices, workdir='tmpdir_test_2D_geometric_decomposition_python' + python_major_version) )

        target_general_Jacobian = sp.sympify('x1**-2 * x2**-2 * x3')
        target_general_poly = sp.sympify('x1**-1 * x2**-1 * x3 * (x1 + x2 + x3)')

        self.assertEqual(len(subsectors), 3)

        for i,subsector in enumerate(subsectors):
            Jacobian = sp.sympify(subsector.Jacobian)
            poly = sp.sympify(subsector.cast[0])

            target_Jacobian = target_general_Jacobian.subs('x%i'%(i+1), 1)
            target_poly = target_general_poly.subs('x%i'%(i+1), 1)
            for j in range(i+1,3+1):
                target_Jacobian = target_Jacobian.subs('x%i'%j, 'x%i'%(j-1))
                target_poly = target_poly.subs('x%i'%j, 'x%i'%(j-1))

            self.assertEqual( (poly-target_poly).simplify() , 0)
            self.assertEqual( (Jacobian-target_Jacobian).simplify() , 0)

    #@attr('active')
    def test_2D_geometric_decomposition_ku(self):
        poly = Polynomial.from_expression('A*x1 + B*x2 + C*x1*x2', ['dummy','x1','x2'])
        sector = Sector([poly])
        indices = [1,2]
        subsectors = list( geometric_decomposition_ku(sector, indices, workdir='tmpdir_test_2D_geometric_decomposition_ku_python' + python_major_version) )
        print(subsectors)
        self.assertEqual(len(subsectors), 2)

        target_Jacobians = [sp.sympify('x2**1 '), sp.sympify('x1**1 ')]
        target_polys = [sp.sympify('x2**1 * (A*x1 + B + C*x1*x2)'), sp.sympify('x1**1 * (A + B*x2 + C*x1*x2)')]

        try:
            for target_poly, target_Jacobian, subsector in zip(target_polys, target_Jacobians,subsectors):
                try:
                    self.assertEqual( (sp.sympify(subsector.cast[0])-target_poly).simplify() , 0)
                    self.assertEqual( (sp.sympify(subsector.Jacobian)-target_Jacobian).simplify() , 0)
                except AssertionError:
                    self.assertEqual( (sp.sympify(subsector.cast[0])-target_poly.subs([('x1','x2'),('x2','x1')],simultaneous=True)).simplify() , 0)
                    self.assertEqual( (sp.sympify(subsector.Jacobian)-target_Jacobian.subs([('x1','x2'),('x2','x1')],simultaneous=True)).simplify() , 0)
        except AssertionError:
            for target_poly, target_Jacobian, subsector in zip(target_polys, target_Jacobians,reversed(subsectors)):
                try:
                    self.assertEqual( (sp.sympify(subsector.cast[0])-target_poly).simplify() , 0)
                    self.assertEqual( (sp.sympify(subsector.Jacobian)-target_Jacobian).simplify() , 0)
                except AssertionError:
                    self.assertEqual( (sp.sympify(subsector.cast[0])-target_poly.subs([('x1','x2'),('x2','x1')],simultaneous=True)).simplify() , 0)
                    self.assertEqual( (sp.sympify(subsector.Jacobian)-target_Jacobian.subs([('x1','x2'),('x2','x1')],simultaneous=True)).simplify() , 0)


    #@attr('active')
    def test_3D_geometric_decomposition(self):
        # 3D test case where triangulation is needed
        poly = Polynomial.from_expression('A*1 + B*x1 + C*x2 + D*x3 + E*x1*x2', ['x1','x2','x3']) # pyramid
        sector = Sector([poly])
        subsectors = list( geometric_decomposition(sector, workdir='tmpdir_test_3D_geometric_decomposition_python' + python_major_version) )

    #@attr('active')
    def test_3D_geometric_decomposition_selected_indices(self):
        # 3D test case where triangulation is needed
        poly = Polynomial.from_expression('A*1 + B*x1 + C*x2 + D*x3 + E*x1*x2', ['x1','dummy','x2','x3']) # pyramid
        sector = Sector([poly])
        indices = [0,2,3]
        subsectors = list( geometric_decomposition(sector, indices, workdir='tmpdir_test_3D_geometric_decomposition_selected_indices_python' + python_major_version) )

class TestPolytope(unittest.TestCase):
    def setUp(self):
        self.vertices = [[2,1],
                         [1,2],
                         [2,0],
                         [1,0],
                         [0,2],
                         [0,1]]

        self.vertices_with_inside = [[1,1]] + self.vertices

        self.facets = [[ 0, 1, 0],
                       [ 1, 0, 0],
                       [-1, 0, 2],
                       [ 0,-1, 2],
                       [ 1, 1,-1],
                       [-1,-1, 3]]

        self.facets_with_outside = [[ 0, 1, 5]] + self.facets

    def test_init(self):
        # must provide either facets or vertices
        self.assertRaisesRegexp(TypeError, 'either.*vertices.*or.*facets', Polytope, facets=self.facets, vertices=self.vertices)
        self.assertRaisesRegexp(TypeError, 'either.*vertices.*or.*facets', Polytope)

        inarray = np.array([[1,2,3],
                            [4,5,6]])

        polytope1 = Polytope(facets=inarray)
        polytope2 = Polytope(vertices=inarray)

        inarray[0,0] = 10

        self.assertEqual(polytope1.facets[0,0], 1)
        self.assertEqual(polytope2.vertices[0,0], 1)

    #@attr('active')
    @attr('slow')
    def test_large_array(self):
        # numpy abbreviates long output by default, but we do not want that
        from numpy import array
        long_array = \
        array([[0, 0, 0, 2, 1, 1],
               [0, 0, 0, 2, 1, 3],
               [0, 0, 0, 2, 3, 1],
               [0, 0, 0, 3, 1, 3],
               [0, 0, 0, 3, 3, 1],
               [0, 0, 0, 4, 1, 1],
               [0, 0, 0, 4, 1, 3],
               [0, 0, 0, 4, 2, 3],
               [0, 0, 0, 4, 3, 1],
               [0, 0, 0, 4, 3, 2],
               [0, 0, 1, 2, 1, 0],
               [0, 0, 1, 2, 3, 0],
               [0, 0, 1, 3, 3, 0],
               [0, 0, 1, 3, 4, 1],
               [0, 0, 1, 4, 1, 0],
               [0, 0, 1, 4, 3, 0],
               [0, 0, 2, 0, 1, 1],
               [0, 0, 2, 0, 1, 3],
               [0, 0, 2, 0, 3, 1],
               [0, 0, 2, 1, 1, 0],
               [0, 0, 2, 1, 3, 0],
               [0, 0, 2, 3, 4, 0],
               [0, 0, 2, 4, 3, 0],
               [0, 0, 3, 0, 1, 1],
               [0, 0, 3, 0, 1, 3],
               [0, 0, 3, 0, 3, 1],
               [0, 0, 3, 1, 1, 0],
               [0, 0, 3, 1, 1, 3],
               [0, 0, 3, 1, 2, 3],
               [0, 0, 3, 1, 3, 0],
               [0, 0, 3, 1, 4, 1],
               [0, 0, 3, 2, 4, 0],
               [0, 0, 3, 4, 1, 0],
               [0, 0, 3, 4, 2, 0],
               [0, 1, 0, 2, 0, 1],
               [0, 1, 0, 2, 0, 3],
               [0, 1, 0, 3, 0, 3],
               [0, 1, 0, 3, 1, 4],
               [0, 1, 0, 4, 0, 1],
               [0, 1, 0, 4, 0, 3],
               [0, 1, 1, 1, 0, 0],
               [0, 1, 1, 4, 0, 0],
               [0, 1, 2, 0, 0, 0],
               [0, 1, 2, 0, 0, 3],
               [0, 1, 2, 0, 3, 0],
               [0, 1, 3, 0, 0, 0],
               [0, 1, 3, 0, 0, 3],
               [0, 1, 3, 0, 1, 4],
               [0, 1, 3, 0, 3, 0],
               [0, 1, 3, 0, 4, 1],
               [0, 1, 3, 1, 0, 3],
               [0, 1, 3, 4, 0, 0],
               [0, 2, 0, 0, 1, 1],
               [0, 2, 0, 0, 1, 3],
               [0, 2, 0, 0, 3, 1],
               [0, 2, 0, 1, 0, 1],
               [0, 2, 0, 1, 0, 3],
               [0, 2, 0, 3, 0, 4],
               [0, 2, 0, 4, 0, 3],
               [0, 2, 1, 0, 0, 0],
               [0, 2, 1, 0, 0, 3],
               [0, 2, 1, 0, 3, 0],
               [0, 2, 3, 0, 0, 0],
               [0, 2, 3, 0, 0, 4],
               [0, 2, 3, 0, 4, 0],
               [0, 2, 3, 4, 0, 0],
               [0, 3, 0, 0, 1, 1],
               [0, 3, 0, 0, 1, 3],
               [0, 3, 0, 0, 3, 1],
               [0, 3, 0, 1, 0, 1],
               [0, 3, 0, 1, 0, 3],
               [0, 3, 0, 1, 1, 4],
               [0, 3, 0, 1, 3, 1],
               [0, 3, 0, 1, 3, 2],
               [0, 3, 0, 2, 0, 4],
               [0, 3, 0, 4, 0, 1],
               [0, 3, 0, 4, 0, 2],
               [0, 3, 1, 0, 0, 0],
               [0, 3, 1, 0, 0, 3],
               [0, 3, 1, 0, 1, 4],
               [0, 3, 1, 0, 3, 0],
               [0, 3, 1, 0, 4, 1],
               [0, 3, 1, 1, 3, 0],
               [0, 3, 1, 4, 0, 0],
               [0, 3, 2, 0, 0, 0],
               [0, 3, 2, 0, 0, 4],
               [0, 3, 2, 0, 4, 0],
               [0, 3, 2, 4, 0, 0],
               [1, 0, 0, 2, 0, 0],
               [1, 0, 0, 2, 0, 2],
               [1, 0, 0, 2, 2, 0],
               [1, 0, 0, 3, 0, 2],
               [1, 0, 0, 3, 2, 0],
               [1, 0, 0, 4, 0, 0],
               [1, 0, 0, 4, 0, 2],
               [1, 0, 0, 4, 2, 0],
               [1, 0, 0, 4, 2, 2],
               [1, 0, 1, 1, 0, 0],
               [1, 0, 1, 1, 0, 2],
               [1, 0, 1, 1, 3, 0],
               [1, 0, 1, 2, 3, 0],
               [1, 0, 2, 1, 0, 0],
               [1, 0, 2, 1, 0, 2],
               [1, 0, 2, 1, 3, 0],
               [1, 0, 2, 2, 0, 2],
               [1, 0, 2, 2, 4, 0],
               [1, 0, 2, 4, 0, 0],
               [1, 0, 2, 4, 2, 0],
               [1, 1, 0, 1, 0, 0],
               [1, 1, 0, 1, 0, 3],
               [1, 1, 0, 1, 2, 0],
               [1, 1, 0, 2, 0, 3],
               [1, 1, 1, 0, 0, 0],
               [1, 1, 1, 0, 0, 3],
               [1, 1, 1, 0, 3, 0],
               [1, 1, 2, 0, 0, 0],
               [1, 1, 2, 0, 0, 3],
               [1, 1, 2, 0, 3, 0],
               [1, 2, 0, 1, 0, 0],
               [1, 2, 0, 1, 0, 3],
               [1, 2, 0, 1, 2, 0],
               [1, 2, 0, 2, 0, 4],
               [1, 2, 0, 2, 2, 0],
               [1, 2, 0, 4, 0, 0],
               [1, 2, 0, 4, 0, 2],
               [1, 2, 1, 0, 0, 0],
               [1, 2, 1, 0, 0, 3],
               [1, 2, 1, 0, 3, 0],
               [1, 2, 2, 0, 0, 0],
               [1, 2, 2, 0, 0, 4],
               [1, 2, 2, 0, 4, 0],
               [1, 2, 2, 4, 0, 0],
               [2, 0, 0, 0, 1, 1],
               [2, 0, 0, 0, 1, 3],
               [2, 0, 0, 0, 3, 1],
               [2, 0, 0, 1, 0, 0],
               [2, 0, 0, 1, 0, 2],
               [2, 0, 0, 1, 1, 3],
               [2, 0, 0, 1, 2, 0],
               [2, 0, 0, 1, 3, 1],
               [2, 0, 0, 2, 0, 2],
               [2, 0, 0, 2, 1, 3],
               [2, 0, 0, 2, 2, 0],
               [2, 0, 0, 2, 2, 3],
               [2, 0, 0, 2, 3, 1],
               [2, 0, 0, 2, 3, 2],
               [2, 0, 0, 3, 0, 2],
               [2, 0, 0, 3, 2, 0],
               [2, 0, 0, 3, 2, 2],
               [2, 0, 0, 4, 0, 0],
               [2, 0, 0, 4, 0, 1],
               [2, 0, 0, 4, 1, 0],
               [2, 0, 0, 4, 1, 1],
               [2, 0, 1, 0, 1, 1],
               [2, 0, 1, 0, 1, 3],
               [2, 0, 1, 0, 3, 1],
               [2, 0, 1, 1, 0, 0],
               [2, 0, 1, 1, 0, 2],
               [2, 0, 1, 1, 1, 3],
               [2, 0, 1, 1, 2, 0],
               [2, 0, 1, 1, 2, 3],
               [2, 0, 1, 1, 4, 1],
               [2, 0, 1, 2, 0, 2],
               [2, 0, 1, 2, 3, 0],
               [2, 0, 1, 3, 2, 1],
               [2, 0, 1, 4, 0, 0],
               [2, 0, 1, 4, 1, 0],
               [2, 1, 0, 0, 1, 1],
               [2, 1, 0, 0, 1, 3],
               [2, 1, 0, 0, 3, 1],
               [2, 1, 0, 1, 0, 0],
               [2, 1, 0, 1, 0, 2],
               [2, 1, 0, 1, 1, 4],
               [2, 1, 0, 1, 2, 0],
               [2, 1, 0, 1, 3, 1],
               [2, 1, 0, 1, 3, 2],
               [2, 1, 0, 2, 0, 3],
               [2, 1, 0, 2, 2, 0],
               [2, 1, 0, 3, 1, 2],
               [2, 1, 0, 4, 0, 0],
               [2, 1, 0, 4, 0, 1],
               [2, 1, 1, 0, 1, 1],
               [2, 1, 1, 0, 1, 4],
               [2, 1, 1, 0, 4, 1],
               [2, 1, 1, 1, 0, 0],
               [2, 1, 1, 1, 0, 3],
               [2, 1, 1, 1, 3, 0],
               [2, 1, 1, 3, 1, 1],
               [2, 1, 1, 4, 0, 0]])

        # error if output abbreviated by numpy
        Polytope(vertices=long_array).complete_representation(workdir='tmpdir_test_large_array_vertices_python' + python_major_version)
        Polytope(facets=long_array).complete_representation(workdir='tmpdir_test_large_array_facets_python' + python_major_version)

    #@attr('active')
    def test_vertex_incidence_lists(self):
        polytopes = [
                        Polytope(vertices=self.vertices_with_inside),
                        Polytope(facets=self.facets_with_outside),
                        Polytope(facets=self.facets),
                        Polytope(vertices=self.vertices)
                    ]

        incidences = []
        for polytope in polytopes:
            # sensible error message if `complete_representaion` not run before?
            self.assertRaisesRegexp(AssertionError, 'complete_representation.*first', polytope.vertex_incidence_lists)

            polytope.complete_representation(workdir='tmpdir_test_vertex_incidence_lists_python' + python_major_version)
            incidences.append(polytope.vertex_incidence_lists())

        target_incidence_lists = {
                                     (1,0): np.array([[ 0, 1, 0], [ 1, 1,-1]]),
                                     (0,1): np.array([[ 1, 0, 0], [ 1, 1,-1]]),
                                     (2,0): np.array([[ 0, 1, 0], [-1, 0, 2]]),
                                     (0,2): np.array([[ 1, 0, 0], [ 0,-1, 2]]),
                                     (2,1): np.array([[-1, 0, 2], [-1,-1, 3]]),
                                     (1,2): np.array([[ 0,-1, 2], [-1,-1, 3]])
                                 }
        for polytope, incidence in zip(polytopes,incidences):
            self.assertEqual(len(incidence.keys()), 6)
            for key, value in incidence.items():
                self.assertTrue(key in target_incidence_lists.keys())

                # The ordering is not important but must be fixed to compare the arrays
                np.testing.assert_array_equal(sort_2D_array(polytope.facets[value]), sort_2D_array(target_incidence_lists[key]))

    def test_vertex2facet(self):
        polytope1 = Polytope(vertices=self.vertices)
        polytope2 = Polytope(vertices=self.vertices_with_inside)

        # useful error message?
        for polytope in (polytope1, polytope2):
            self.assertRaisesRegexp(
                                        OSError, 'No such file or directory.*nonexistentNormalizExecutable',
                                        polytope.complete_representation, normaliz='nonexistentNormalizExecutable',
                                        workdir='tmpdir_test_vertex2facet_python' + python_major_version
                                   )

        polytope1.complete_representation(workdir='tmpdir1_test_vertex2facet_python' + python_major_version)
        polytope2.complete_representation(workdir='tmpdir2_test_vertex2facet_python' + python_major_version)

        self.assertRaisesRegexp(ValueError, '(B|b)oth.*already', polytope1.complete_representation, workdir='tmpdir3_test_vertex2facet_python' + python_major_version)
        self.assertRaisesRegexp(ValueError, '(B|b)oth.*already', polytope2.complete_representation, workdir='tmpdir4_test_vertex2facet_python' + python_major_version)

        # The ordering is not important but must be fixed to compare the arrays
        np.testing.assert_array_equal( sort_2D_array(np.array(polytope1.vertices)), sort_2D_array(np.array(self.vertices)) )
        np.testing.assert_array_equal( sort_2D_array(np.array(polytope2.vertices)), sort_2D_array(np.array(self.vertices)) )
        np.testing.assert_array_equal( sort_2D_array(np.array(polytope1.facets)), sort_2D_array(np.array(self.facets)) )
        np.testing.assert_array_equal( sort_2D_array(np.array(polytope2.facets)), sort_2D_array(np.array(self.facets)) )

    def test_facet2vertex(self):
        polytope1 = Polytope(facets=self.facets)
        polytope2 = Polytope(facets=self.facets_with_outside)

        # useful error message?
        for polytope in (polytope1, polytope2):
            self.assertRaisesRegexp(
                                        OSError, 'No such file or directory.*nonexistentNormalizExecutable',
                                        polytope.complete_representation, normaliz='nonexistentNormalizExecutable',
                                        workdir='tmpdir_test_facet2vertex_python' + python_major_version
                                   )

        polytope1.complete_representation(workdir='tmpdir1_test_facet2vertex_python' + python_major_version)
        polytope2.complete_representation(workdir='tmpdir2_test_facet2vertex_python' + python_major_version)

        self.assertRaisesRegexp(ValueError, '(B|b)oth.*already', polytope1.complete_representation, workdir='tmpdir3_test_facet2vertex_python' + python_major_version)
        self.assertRaisesRegexp(ValueError, '(B|b)oth.*already', polytope2.complete_representation, workdir='tmpdir4_test_facet2vertex_python' + python_major_version)

        # The ordering is not important but must be fixed to compare the arrays
        np.testing.assert_array_equal( sort_2D_array(np.array(polytope1.vertices)), sort_2D_array(np.array(self.vertices)) )
        np.testing.assert_array_equal( sort_2D_array(np.array(polytope2.vertices)), sort_2D_array(np.array(self.vertices)) )
        np.testing.assert_array_equal( sort_2D_array(np.array(polytope1.facets)), sort_2D_array(np.array(self.facets)) )
        np.testing.assert_array_equal( sort_2D_array(np.array(polytope2.facets)), sort_2D_array(np.array(self.facets)) )
