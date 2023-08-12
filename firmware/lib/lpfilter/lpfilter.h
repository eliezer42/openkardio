
#ifndef LPFILTER_H_ // Include guards
#define LPFILTER_H_

/*
Generated code is based on the following filter design:
<micro.DSP.FilterDocument sampleFrequency="#1" arithmetic="float" biquads="Direct1" classname="lpfilter" inputMax="#1" inputShift="#15" >
  <micro.DSP.ParksMcClellanDesigner N="#21" firtype="2" symmetry="+" evenodd="#1" >
    <micro.DSP.FilterStructure coefficientBits="#0" variableBits="#0" accumulatorBits="#0" biquads="Direct1" >
      <micro.DSP.FilterSection form="Fir" historyType="Double" accumulatorBits="#0" variableBits="#0" coefficientBits="#0" />
    </micro.DSP.FilterStructure>
    <micro.DSP.PoleOrZeroContainer >
      <micro.DSP.ReciprocalZero i="#0.2009124709948921" r="#0.5999215914555297" isPoint="#true" isPole="#false" isZero="#true" symmetry="i" N="#1" cascade="#0" />
      <micro.DSP.ReciprocalZero i="#0.5344253482405539" r="#0.3703207495806691" isPoint="#true" isPole="#false" isZero="#true" symmetry="i" N="#1" cascade="#0" />
      <micro.DSP.UnitZero i="#0.9451526597837403" r="#-0.3266289174334095" isPoint="#true" isPole="#false" isZero="#true" symmetry="u" N="#1" cascade="#0" />
      <micro.DSP.UnitZero i="#0.8863058183865189" r="#-0.46310041707409755" isPoint="#true" isPole="#false" isZero="#true" symmetry="u" N="#1" cascade="#0" />
      <micro.DSP.UnitZero i="#0.7217032906837916" r="#-0.6922025427692292" isPoint="#true" isPole="#false" isZero="#true" symmetry="u" N="#1" cascade="#0" />
      <micro.DSP.UnitZero i="#0.4732778285141956" r="#-0.88091321765364" isPoint="#true" isPole="#false" isZero="#true" symmetry="u" N="#1" cascade="#0" />
      <micro.DSP.UnitZero i="#0.16482358722651594" r="#-0.9863230632474193" isPoint="#true" isPole="#false" isZero="#true" symmetry="u" N="#1" cascade="#0" />
      <micro.DSP.ReciprocalZero i="#0" r="#-0.16266177765630127" isPoint="#true" isPole="#false" isZero="#true" symmetry="i" N="#1" cascade="#0" />
    </micro.DSP.PoleOrZeroContainer>
    <micro.DSP.GenericC.CodeGenerator generateTestCases="#false" />
    <micro.DSP.LowPassSpecification bandType="l" N="#27" f1="#0.2" f2="#0.4" stopRipple="#0.03162277660168377" passRipple="#0.05750112778453722" transition="#0.1" passGain="#1" stopGain="#0" >
      <micro.DSP.ControlPoint start="#0" ripple="#0.05750112778453722" gain="#1" interpolation="linear" />
      <micro.DSP.ControlPoint start="#0.2" ripple="#0" gain="#1" interpolation="cosine" />
      <micro.DSP.ControlPoint start="#0.30000000000000004" ripple="#0.03162277660168377" gain="#0" interpolation="linear" />
      <micro.DSP.ControlPoint start="#0.5" ripple="#0" gain="#0" interpolation="linear" />
    </micro.DSP.LowPassSpecification>
  </micro.DSP.ParksMcClellanDesigner>
</micro.DSP.FilterDocument>

*/

static const int lpfilter_length = 480;
extern float lpfilter_coefficients[480];

typedef struct
{
	float * pointer;
	float state[960];
	float output;
} lpfilterType;


lpfilterType *lpfilter_create( void );
void lpfilter_destroy( lpfilterType *pObject );
void lpfilter_init( lpfilterType * pThis );
void lpfilter_reset( lpfilterType * pThis );
#define lpfilter_writeInput( pThis, input )  \
    lpfilter_filterBlock( pThis, &(input), &(pThis)->output, 1 );

#define lpfilter_readOutput( pThis )  \
    (pThis)->output

int lpfilter_filterBlock( lpfilterType * pThis, float * pInput, float * pOutput, unsigned int count );
#define lpfilter_outputToFloat( output )  \
    (output)

#define lpfilter_inputFromFloat( input )  \
    (input)

void lpfilter_dotProduct( float * pInput, float * pKernel, float * pAccumulator, short count );
#endif // LPFILTER_H_
	
