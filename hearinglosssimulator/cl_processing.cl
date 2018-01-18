

#define chunksize %(chunksize)d
#define nb_level %(nb_level)d
//#define calibration %(calibration)8.4f
//#define levelstep %(levelstep)8.4f
#define levelmax %(levelmax)d



//__constant int  nb_level = %(nb_level)d;
__constant float calibration = %(calibration)8.4ff;
__constant float levelstep = %(levelstep)8.4ff;
//__constant int levelmax = %(levelmax)d;

__kernel void sos_filter(__global  float *input, __global  float *output, __constant  float *coefficients, 
            __global float *zi, int direction, int nb_section) {
    /*
    This implement direct form II of lfilter
    https://ccrma.stanford.edu/~jos/fp/Direct_Form_II.html
    input shape is (total_channel, nb_section)
    output shape is (total_channel, nb_section)
    coefficient shape is (total_channel, nb_section, 6)
    zi shape is (total_channel, nb_section, 2)
    */                                                                        
    
    int chan = get_global_id(0); //channel indice
    int section = get_global_id(1); //section indice

    int offset_buf = chan*chunksize;
    int offset_filt = chan*nb_section*6; //offset channel
    int offset_filt2;  //offset channel within section
    int offset_zi = chan*nb_section*2;


    // copy channel to local group
    __local float out_channel[chunksize];
    if (section ==0) for (int s=0; s<chunksize;s++) out_channel[s] = input[offset_buf+s];
    
    float w0, w1,w2;
    //float y0;
    
    
    
    w1 = zi[offset_zi+section*2+0];
    w2 = zi[offset_zi+section*2+1];
    int s2;
    for (int s=0; s<chunksize+(3*nb_section);s++){
        barrier(CLK_LOCAL_MEM_FENCE);

        s2 = s-section*3;
        
        if (s2>=0 && (s2<chunksize)){
        
            if (direction==-1) s2 = chunksize - s2 - 1;  //this is for bacward
            
            offset_filt2 = offset_filt+section*6;
            w0 = out_channel[s2];
            w0 -= coefficients[offset_filt2+4] * w1;
            w0 -= coefficients[offset_filt2+5] * w2;
            out_channel[s2] = coefficients[offset_filt2+0] * w0 + coefficients[offset_filt2+1] * w1 +  coefficients[offset_filt2+2] * w2;
            w2 = w1; w1 =w0;
        }
    }
    zi[offset_zi+section*2+0] = w1;
    zi[offset_zi+section*2+1] = w2;
    
    if (section ==(nb_section-1)){
        for (int s=0; s<chunksize;s++) output[offset_buf+s] = out_channel[s];
    }

}


/*
__kernel void forward_filter(__global  float *input, __global  float *output, __constant  float *coefficients, __global float *zi,  int nb_section){
    sos_filter(input, output, coefficients, zi,  1, nb_section);
}

__kernel void backward_filter(__global  float *input, __global  float *output, __constant  float *coefficients, __global float *zi,  int nb_section) {
    sos_filter(input, output, coefficients, zi,  -1, nb_section);
}
*/


/*
    //int offset_level = chan*levelavgsize;
    
    //int pos = ((chunksize*chunkcount-1)%%levelavgsize);

    //float prevlevel = previouslevel[offset_level+pos];
    //float prevlevel = previouslevel[offset_level];


        //for (int k=levelavgsize-1; k>0; k--) previouslevel[offset_level+k] = previouslevel[offset_level+k-1];

        //pos += 1;
        //if (pos == levelavgsize) pos=0;
        //previouslevel[offset_level+pos] = prevlevel;

        //average on a window
        //avlevel = 0.0;
        //for (int k=0; k<levelavgsize; k++) avlevel += (previouslevel[offset_level+k]);
        //avlevel /= levelavgsize;

        //if (avlevel>=levelmax) avlevel = levelmax-levelstep;

*/

__kernel void estimate_leveldb(__global  float *input, __global  float *outlevels, __global float *previouslevel, __constant float *expdecays, long chunkcount) {

    int chan = get_global_id(0);
    
    int offset_buf = chan*chunksize;
    float level = previouslevel[chan];
    float db_level;
    float expdecay = expdecays[chan];
    
    for (int s=0; s<chunksize;s++) {
        
        
        level = max( fabs(input[offset_buf+s]), level*expdecay);
        previouslevel[chan] = level;
        
        //to dB and index dB
        db_level = (20*log10(level) + (float) calibration);
        
        //clip
        if (db_level>levelmax) db_level = levelmax;
        if (db_level<0.0f) db_level = 0.0f;
        
        outlevels[offset_buf+s] = db_level;
    }
}



__kernel void dynamic_sos_filter(__global  float *input, __global  float * levels, __global  float *output, __global float *coefficients, __global float *zis, int nb_section) {

    int chan = get_global_id(0); //channel indice
    int section = get_global_id(1); //section indice

    int offset_buf = chan*chunksize;
    int offset_filt = chan*nb_level*nb_section*6;
    int offset_filt2;  //offset channel within section
    int offset_zi = chan*nb_section*2;

    
    // copy channel to local group
    __local float out_channel[chunksize];
    if (section ==0) for (int s=0; s<chunksize;s++) out_channel[s] = input[offset_buf+s];

    float w0, w1,w2;
    //float y0;
    int filterindex;
    
    w1 = zis[offset_zi+section*2+0];
    w2 = zis[offset_zi+section*2+1];
    int s2;
    for (int s=0; s<chunksize+(3*nb_section);s++){
        barrier(CLK_LOCAL_MEM_FENCE);
        s2 = s-section*3;
        
        //filtering
        if (s2>=0 && (s2<chunksize)){
            //filterindex = (int) levels[offset_buf+s2];
            filterindex = (int) (levels[offset_buf+s2]/ levelstep);
            
            offset_filt2 = offset_filt+filterindex*nb_section*6+section*6;
            w0 = out_channel[s2];
            w0 -= coefficients[offset_filt2+4] * w1;
            w0 -= coefficients[offset_filt2+5] * w2;
            out_channel[s2] = coefficients[offset_filt2+0] * w0 + coefficients[offset_filt2+1] * w1 +  coefficients[offset_filt2+2] * w2;
            w2 = w1; w1 =w0;
        }
    }
    zis[offset_zi+section*2+0] = w1;
    zis[offset_zi+section*2+1] = w2;
    
    if (section ==(nb_section-1)){
        for (int s=0; s<chunksize;s++) output[offset_buf+s] = out_channel[s];
    }
}


__kernel void reset_zis(__global  float *zis){
    int chan = get_group_id(0);
    zis[2*chan] = 0;
    zis[2*chan+1] = 0;    
}



__kernel void dynamic_gain(__global  float *input, __global  float * levels, __global  float *output, __global float *gain_controlled) {
    
    int chan = get_global_id(0); //channel indice
    int pos = get_global_id(1); //sample index
    
    int offset_buf = chan*chunksize;
    int gainindex = (int) (levels[offset_buf+pos]/ levelstep);
    output[offset_buf+pos] = input[offset_buf+pos] * gain_controlled[chan*nb_level+gainindex];
    
}





__kernel void transpose_and_repeat_channel(__global float *inbuffer, __global float *output,  int shape_in_1,   int nb_repeat){

    int r = get_global_id(0);
    int chan = get_global_id(1);
    
    int offset_out = (chan*nb_repeat*chunksize) + r*chunksize;
    
    for (int s=0; s<chunksize;s++) output[offset_out+s] = inbuffer[shape_in_1*s+chan];
    
}



__kernel void bychannel_gain(__global float *inbuffer, __global float *output, __global float *gains){

    int chan = get_global_id(0);
    int pos = get_global_id(1);
    
    int offset = chan*chunksize + pos;
    output[offset] = inbuffer[offset]*gains[chan];
    
}


__kernel void sum_channel_and_gain(__global float *input,  __global float *output, 
                                                int nb_repeat, int nb_channel, float band_overlap_gain){
    int s = get_global_id(0);//sample pos
    int chan;
    
    for (int c=0; c<nb_channel;c++){
        float sum= 0;
        for (int r=0; r<nb_repeat; r++){
            chan = nb_repeat*c + r;
            sum += input[chan*chunksize+s];
        }
        //written in order (sample, channel)
        output[s*nb_channel+c] = sum * band_overlap_gain;
    }
}

