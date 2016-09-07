

#define forward_chunksize %(forward_chunksize)d
#define backward_chunksize %(backward_chunksize)d
#define nb_channel %(nb_channel)d
#define max_chunksize %(max_chunksize)d

#define nb_level %(nb_level)d
#define levelavgsize %(levelavgsize)d
#define calibration %(calibration)8.4f
#define levelstep %(levelstep)8.4f
#define levelmax %(levelmax)d


__kernel void sos_filter(__global  float *input, __global  float *output, __constant  float *coefficients, 
            __global float *zi, int chunksize, int direction, int nb_section) {
    /*
    This implement direct form II of lfilter
    https://ccrma.stanford.edu/~jos/fp/Direct_Form_II.html
    input shape is (nb_channel, nb_section)
    output shape is (nb_channel, nb_section)
    coefficient shape is (nb_channel, nb_section, 6)
    zi shape is (nb_channel, nb_section, 2)
    */                                                                        
    
    int chan = get_global_id(0); //channel indice
    int section = get_global_id(1); //section indice

    int offset_buf = chan*chunksize;
    int offset_filt = chan*nb_section*6; //offset channel
    int offset_filt2;  //offset channel within section
    int offset_zi = chan*nb_section*2;


    // copy channel to local group
    __local float out_channel[max_chunksize];
    if (section ==0) for (int s=0; s<chunksize;s++) out_channel[s] = input[offset_buf+s];
    
    float w0, w1,w2;
    float y0;
    
    
    
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


__kernel void forward_filter(__global  float *input, __global  float *output, __constant  float *coefficients, __global float *zi,  int nb_section){
    sos_filter(input, output, coefficients, zi, forward_chunksize, 1, nb_section);
}

__kernel void backward_filter(__global  float *input, __global  float *output, __constant  float *coefficients, __global float *zi,  int nb_section) {
    sos_filter(input, output, coefficients, zi, backward_chunksize, -1, nb_section);
}




__kernel void estimate_leveldb(__global  float *input, __global  float *outlevels, __global float *previouslevel, __constant float *expdecays, long chunkcount) {

    int chan = get_global_id(0);
    
    int offset_buf = chan*forward_chunksize;
    int offset_level = chan*levelavgsize;
    
    int pos = ((forward_chunksize*chunkcount-1)%%levelavgsize);

    float prevlevel = previouslevel[offset_level+pos];
    float avlevel;
    float expdecay = expdecays[chan];
    
    for (int s=0; s<forward_chunksize;s++) {
        //for (int k=levelavgsize-1; k>0; k--) previouslevel[offset_level+k] = previouslevel[offset_level+k-1];
        
        prevlevel = max( fabs(input[offset_buf+s]), prevlevel*expdecay);
        pos += 1;
        if (pos == levelavgsize) pos=0;
        previouslevel[offset_level+pos] = prevlevel;
        
        //average on a window
        avlevel = 0.0;
        for (int k=0; k<levelavgsize; k++) avlevel += (previouslevel[offset_level+k]);
        avlevel /= levelavgsize;
        //avlevel = prevlevel;
        
        //to dB and index dB
        avlevel = (20*log10(avlevel) + calibration);
        if (avlevel>=levelmax) avlevel = levelmax-levelstep;
        if (avlevel<0.0f) avlevel = 0.0f;
        //outlevels[offset_buf+s] = avlevel/levelstep;
        outlevels[offset_buf+s] = avlevel;
    }
}



__kernel void dynamic_sos_filter(__global  float *input, __global  float * levels, __global  float *output, __global float *coefficients, __global float *zis, int nb_section) {

    int chan = get_global_id(0); //channel indice
    int section = get_global_id(1); //section indice

    int offset_buf = chan*forward_chunksize;
    int offset_filt = chan*nb_level*nb_section*6;
    int offset_filt2;  //offset channel within section
    int offset_zi = chan*nb_section*2;

    
    // copy channel to local group
    __local float out_channel[forward_chunksize];
    if (section ==0) for (int s=0; s<forward_chunksize;s++) out_channel[s] = input[offset_buf+s];

    float w0, w1,w2;
    float y0;
    int filterindex;
    
    w1 = zis[offset_zi+section*2+0];
    w2 = zis[offset_zi+section*2+1];
    int s2;
    for (int s=0; s<forward_chunksize+(3*nb_section);s++){
        barrier(CLK_LOCAL_MEM_FENCE);
        s2 = s-section*3;
        
        //filtering
        if (s2>=0 && (s2<forward_chunksize)){
            //filterindex = (int) levels[offset_buf+s2];
            filterindex = (int) (levels[offset_buf+s2]/levelstep);
            
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
        for (int s=0; s<forward_chunksize;s++) output[offset_buf+s] = out_channel[s];
    }
}