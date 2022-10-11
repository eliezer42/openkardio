/******************************* SOURCE LICENSE *********************************
Copyright (c) 2021 MicroModeler.

A non-exclusive, nontransferable, perpetual, royalty-free license is granted to the Licensee to 
use the following Information for academic, non-profit, or government-sponsored research purposes.
Use of the following Information under this License is restricted to NON-COMMERCIAL PURPOSES ONLY.
Commercial use of the following Information requires a separately executed written license agreement.

This Information is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

******************************* END OF LICENSE *********************************/

// A commercial license for MicroModeler DSP can be obtained at https://www.micromodeler.com/launch.jsp

#include "lpfilter.h"

#include <stdlib.h> // For malloc/free
#include <string.h> // For memset

float lpfilter_coefficients[36] = 
{
	0.00000000000000,0.00000000000000,0.00000000000000,0.00011388150136817848,
    -0.002921597292146519,-0.006499371904132994,-0.0041476361053438045,0.005965808551728905,
    0.01174526458588886,-0.00015883571876733885,-0.019424856332084867,-0.015468383633845527,
    0.01891056364194401,0.04007594636200051,0.0009719529099817548,-0.06787407291244034,
    -0.05992612021451047,0.09000146817882639,0.3012660937894696,0.401550965705083,
    0.3012660937894696,0.09000146817882639,-0.05992612021451047,-0.06787407291244034,
    0.0009719529099817548,0.04007594636200051,0.01891056364194401,-0.015468383633845527,
    -0.019424856332084867,-0.00015883571876733885,0.01174526458588886,0.005965808551728905,
    -0.0041476361053438045,-0.006499371904132994,-0.002921597292146519,0.00011388150136817848
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


