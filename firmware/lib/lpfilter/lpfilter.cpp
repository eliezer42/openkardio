#include "lpfilter.h"

#include <stdlib.h> // For malloc/free
#include <string.h> // For memset

float lpfilter_coefficients[52] = 
{
    -0.004656318004405627, 0.0004569009298227957, 0.0024217966033922757, 0.004684861893815379, 0.005911428270733918, 0.004923963289002614, 0.0013597792995145826, -0.003883667265059867, -0.008744938489793033, -0.010699039238104122, -0.007916746969875156, -0.0003759665269553883, 0.009622486426806236, 0.017948344854431718, 0.020062780114192214, 0.013064145908364373, -0.0025077187661627347, -0.022013763386495768, -0.03751156643160482, -0.04018234286406491, -0.023470458899338402, 0.014053817803264725, 0.06734006004832002, 0.1256143549458254, 0.17523965924627843, 0.20375892388594258, 0.20375892388594258, 0.17523965924627843, 0.1256143549458254, 0.06734006004832002, 0.014053817803264725, -0.023470458899338402, -0.04018234286406491, -0.03751156643160482, -0.022013763386495768, -0.0025077187661627347, 0.013064145908364373, 0.020062780114192214, 0.017948344854431718, 0.009622486426806236, -0.0003759665269553883, -0.007916746969875156, -0.010699039238104122, -0.008744938489793033, -0.003883667265059867, 0.0013597792995145826, 0.004923963289002614, 0.005911428270733918, 0.004684861893815379, 0.0024217966033922757, 0.0004569009298227957, -0.004656318004405627
};


lpfilterType *lpfilter_create( void )
{
    lpfilterType *result = (lpfilterType *)malloc( sizeof( lpfilterType ) ); // Allocate memory for the object
    lpfilter_init( result );                                               // Initialize it
    return result;                                                        // Return the result
}

void lpfilter_destroy( lpfilterType *pObject )
{
    free( pObject );
}

void lpfilter_init( lpfilterType * pThis )
{
    lpfilter_reset( pThis );
}

void lpfilter_reset( lpfilterType * pThis )
{
    memset( &pThis->state, 0, sizeof( pThis->state ) ); // Reset state to 0
    pThis->pointer = pThis->state;                      // History buffer points to start of state buffer
    pThis->output = 0;                                  // Reset output
}

int lpfilter_filterBlock( lpfilterType * pThis, float * pInput, float * pOutput, unsigned int count )
{
    float *pOriginalOutput = pOutput;               // Save original output so we can track the number of samples processed
    float accumulator;

    for( ;count; --count )
    {
        pThis->pointer[lpfilter_length] = *pInput;                   // Copy sample to top of history buffer
        *(pThis->pointer++) = *(pInput++);                         // Copy sample to bottom of history buffer

        if( pThis->pointer >= pThis->state + lpfilter_length )       // Handle wrap-around
            pThis->pointer -= lpfilter_length;

        accumulator = 0;
        lpfilter_dotProduct( pThis->pointer, lpfilter_coefficients, &accumulator, lpfilter_length );

        *(pOutput++) = accumulator;  // Store the result
    }

    return pOutput - pOriginalOutput;
}

void lpfilter_dotProduct( float * pInput, float * pKernel, float * pAccumulator, short count )
{
    float accumulator = *pAccumulator;
    while( count-- )
        accumulator += ((float)*(pKernel++)) * *(pInput++);
    *pAccumulator = accumulator;
}


