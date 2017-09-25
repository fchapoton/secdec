#include "catch.hpp"
#include "../secdecutil/integrand_container.hpp"
#include "../secdecutil/integrators/integrator.hpp"
#include "../secdecutil/integrators/cquad.hpp"
#include "../secdecutil/uncertainties.hpp"

#include <complex>

using Catch::Matchers::Contains;

TEST_CASE( "Test cquad error message more than 1D", "[Integrator][CQuad]" ) {
    int dimensionality = 4;
    const std::function<double(double const * const)> integrand = [] (double const * const variables) { return 0.0; };
    const auto integrand_container = secdecutil::IntegrandContainer<double, double const * const>(dimensionality,integrand);
    secdecutil::gsl::CQuad<double> integrator;

    REQUIRE_THROWS_AS( integrator.integrate(integrand_container) , std::invalid_argument );
    REQUIRE_THROWS_WITH( integrator.integrate(integrand_container) , "\"CQuad\" can only be used for one dimensional integrands (got ndim=4)." );
};

TEST_CASE( "Test cquad gsl error handling", "[Integrator][CQuad]" ) {
    int dimensionality = 1;
    const std::function<double(double const * const)> integrand = [] (double const * const variables) { return 1./variables[0]; };
    const auto integrand_container = secdecutil::IntegrandContainer<double, double const * const>(dimensionality,integrand);

    REQUIRE_THROWS_AS( secdecutil::gsl::CQuad<double>(1e-2,1e-7,1) , secdecutil::gsl::gsl_error);
    REQUIRE_THROWS_WITH( secdecutil::gsl::CQuad<double>(1e-2,1e-7,1) , Contains("n must be at least 3") );

    secdecutil::gsl::CQuad<double> integrator{-1.0,1e-7,100};

    REQUIRE_THROWS_AS( integrator.integrate(integrand_container) , secdecutil::gsl::gsl_error );
    REQUIRE_THROWS_WITH( integrator.integrate(integrand_container) , Contains( "tolerance" ) && Contains( "invalid" ) );
};

TEST_CASE( "Test cquad member access", "[Integrator][CQuad]" ) {

    SECTION( "real" ) {
        secdecutil::gsl::CQuad<double> real_integrator{1.0,1e-3,8};

        REQUIRE( real_integrator.epsrel == 1.0   );
        REQUIRE( real_integrator.epsabs == 0.001 );
        REQUIRE( real_integrator.n      == 8     );
    }

    SECTION( "complex" ) {
        secdecutil::gsl::CQuad<std::complex<double>> complex_integrator{1.0,1e-3,8};

        REQUIRE( complex_integrator.epsrel == 1.0   );
        REQUIRE( complex_integrator.epsabs == 0.001 );
        REQUIRE( complex_integrator.n      == 8     );
    }

};


TEST_CASE( "Test cquad copy constructor", "[Integrator][CQuad]" ) {
    int dimensionality = 1;

    secdecutil::gsl::CQuad<double> original;
    secdecutil::gsl::CQuad<double> copy = original;

    // new workspace should have been allocated
    REQUIRE( copy.get_workspace() != original.get_workspace() );
};

TEST_CASE( "Test cquad complex to real constructor", "[Integrator][CQuad]" ) {
    int dimensionality = 1;

    secdecutil::gsl::CQuad<std::complex<double>> complex_integrator;
    std::unique_ptr<secdecutil::Integrator<double,double>> generated_real_integrator_ptr = complex_integrator.get_real_integrator();
    secdecutil::gsl::CQuad<double>& generated_real_integrator = *dynamic_cast<secdecutil::gsl::CQuad<double>*>( generated_real_integrator_ptr.get() );

    // workspace of the complex integrator should also be used in generated real integrator
    REQUIRE( complex_integrator.get_workspace().get() == generated_real_integrator.get_workspace().get() );
};


template<typename real_t>
void test_integrator_real(secdecutil::Integrator<real_t,real_t>& integrator, double epsrel, int dimensionality = 1){

    const std::function<real_t(real_t const * const)> integrand =
    [dimensionality] (real_t const * const variables)
    {
        real_t out = 1.;
        for (int i=0; i<dimensionality; ++i)
            out *= 6. * variables[i] * (1. - variables[i]);
        return out;
    };

    const auto integrand_container = secdecutil::IntegrandContainer<real_t, real_t const * const>(dimensionality,integrand);
    double expected_result = 1.;

    auto computed_result = integrator.integrate(integrand_container);

    REQUIRE( computed_result.value > 0.9 );
    REQUIRE( computed_result.value < 1.1 );
    REQUIRE( computed_result.value == Approx( expected_result ).epsilon( epsrel ) );
    REQUIRE( computed_result.uncertainty <= epsrel * computed_result.value );
};

template<typename real_t>
void test_integrator_complex(secdecutil::Integrator<std::complex<real_t>,real_t>& integrator, double epsrel){

    constexpr int dimensionality = 1;

    const std::function<std::complex<real_t>(real_t const * const)> integrand =
    [] (real_t const * const variables)
    {
        real_t out_real = 1.;
        for (int i=0; i<dimensionality; ++i)
            out_real *= 6. * variables[i] * (1. - variables[i]);

        real_t out_imag = variables[0] * (1. - variables[0]);

        return std::complex<real_t>{out_real,out_imag};
    };

    const auto integrand_container = secdecutil::IntegrandContainer<std::complex<real_t>, real_t const * const>(dimensionality,integrand);
    std::complex<double> expected_result = {1.,1./6.};

    auto computed_result = integrator.integrate(integrand_container);

    REQUIRE( computed_result.value.real() > expected_result.real() - 0.1 );
    REQUIRE( computed_result.value.real() < expected_result.real() + 0.1 );

    REQUIRE( computed_result.value.imag() > expected_result.imag() - 0.1 );
    REQUIRE( computed_result.value.imag() < expected_result.imag() + 0.1 );

    REQUIRE( computed_result.value.real() == Approx( expected_result.real() ).epsilon( epsrel ) );
    REQUIRE( computed_result.value.imag() == Approx( expected_result.imag() ).epsilon( epsrel ) );

    REQUIRE( computed_result.uncertainty.real() <= epsrel );
    REQUIRE( computed_result.uncertainty.imag() <= epsrel );
};

TEST_CASE( "Test cquad integrator with real", "[Integrator][CQuad]" ) {
  double epsrel = 1e-10;
  double epsabs = 0.0;
  auto integrator = secdecutil::gsl::CQuad<double>(epsrel,epsabs);
  test_integrator_real(integrator, epsrel);
};

TEST_CASE( "Test cquad integrator with complex", "[Integrator][CQuad]" ) {
  double epsrel = 1e-10;
  double epsabs = 0.0;
  auto integrator = secdecutil::gsl::CQuad<std::complex<double>>(epsrel,epsabs);
  SECTION( "Integrate real and imag separately" ) {
    integrator.together = false; // together = true not implemented for cquad
    test_integrator_complex(integrator, epsrel);
  }
};

TEST_CASE( "Test cquad integrator with long double", "[Integrator][CQuad]" ) {
  double epsrel = 1e-10;
  double epsabs = 0.0;
  auto integrator = secdecutil::gsl::CQuad<long double>();
  integrator.epsrel = epsrel;
  integrator.epsabs = epsabs;
  test_integrator_real(integrator, epsrel);
};

TEST_CASE( "Test Vegas integrator with complex long double", "[Integrator][CQuad]" ) {
  double epsrel = 1e-10;
  double epsabs = 0.0;
  auto integrator = secdecutil::gsl::CQuad<std::complex<long double>>(epsrel);
  integrator.epsabs = epsabs;
  SECTION( "Integrate real and imag separately" ) {
    integrator.together = false; // together = true not implemented for cquad
    test_integrator_complex(integrator, epsrel);
  }
};