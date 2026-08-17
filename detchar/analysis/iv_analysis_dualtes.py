"""
Extensions to ivAnalysis_utils to handle DualTES data
where there might be 2 transitions in 1 iv curve
"""
import numpy as np
import detchar
from matplotlib import pyplot as plt
from .ivAnalysis_utils import IVCurveAnalyzeSingle, IVversusADRTempOneRow

def find_good_region(x, y, good_range, second_good_range, start=0, n_good_thresh=10):
    # warning, this might be a bit slow. Perhaps its time to break out numba again

    start_end_reg=[0,0]
    dy_dx = np.diff(y)/np.diff(x)
    d2y_dx2 = np.diff(np.diff(y))/np.diff(x)[1:]
    idx = find_good_start(x,y,good_range,start=start, n_good_thresh=n_good_thresh)
    found_a_reg = idx is not None
    if found_a_reg:
        # Now that we have identified the start of a good region, we use the 2nd derivative
        # to identify its end point.
        # plt.figure()
        # plt.plot(x[2+start_end_reg[0]:], d2y_dx2[start_end_reg[0]:])
        start_end_reg[0]=idx
        d2_out_range= np.logical_or(d2y_dx2 < second_good_range[0], d2y_dx2 > second_good_range[1])
        bad_idxs = np.nonzero(d2_out_range)[0]
        try:
            start_end_reg[1] = bad_idxs[bad_idxs > start_end_reg[0]][0] +2
        except IndexError:
            start_end_reg[1] = y.shape[0]-start_end_reg[0]
        return start_end_reg   
    else:
        return (0,0)

def find_good_start(x, y, good_range, start=0, n_good_thresh=10):
    """
    Going from low to high index in the array, look for n_good_thresh consecutive points
    that have dy/dx falling inside good_range (i.e. good_range[0] < dy/dx < good_range[1])
    Return the index of the first item in that group of consecutive points.

    If nothing is found, the length of the array is returned
    """
    region_index = len(x)
    dy_dx = np.diff(y)/np.diff(x)
    n_goods=0
    for i in range(start, len(dy_dx)):
        # Look for a number of data points where the derivative of the data is in the good_range
        # This corresponds to a region of constant dynamic resistance.
        if good_range[0] < dy_dx[i] < good_range[1]:
            n_goods+=1
            if n_goods >= n_good_thresh:
                region_index = i-n_good_thresh+1
                break
        else:
            n_goods=0
    return region_index

def find_bad(x, y, good_range, start=0, n_bad_size=10,bad_frac=0.5):
    """
    Going from low to high index in the array, look for a region of n_bad_size in which 
    at least bad_frac fraction of points have d2y/dx outside the "good range"

    Return the index of the first data point where the second derivative lies outside the range, or len(x) if not found
    """
    region_index = len(x)
    d2y_dx2 = np.diff(np.diff(y))/np.diff(x)[1:]
    last_n_results = np.full(n_bad_size,False)
    temp_array = np.copy(last_n_results)
    
    for i in range(start, len(d2y_dx2)):
        #start by shifting the arrays
        temp_array[1:] = last_n_results[0:-1]
        last_n_results[1:] = temp_array[1:]
        
        if good_range[0] > d2y_dx2[i] or d2y_dx2[i] > good_range[1]:
            last_n_results[0] = True # same as masked array, I'll think of True as "bad data"
        else:
            last_n_results[0] = False
        if np.sum(last_n_results) >= n_bad_size * bad_frac:
            region_index = i-np.max(np.nonzero(last_n_results)[0]) + 1
            break
        #print(last_n_results)
    return region_index


class IVAnalyzeDual(IVCurveAnalyzeSingle):
    def __init__(self,x,y,rsh_ohm,normal_r_sci,normal_r_lab,sc_r,target_lab=False,**kwargs):
        self.normal_r_sci = normal_r_sci
        self.normal_r_lab = normal_r_lab
        self.sc_r = sc_r
        self.target_lab=target_lab
        #kwargs["analyze_on_init"]=False
        super().__init__(x,y,rsh_ohm,**kwargs)

    def determine_iv_regimes(self,plot=False):
        """ New DualTES designs using proximity effect can show two TESs in one IV curve. 
            So there will be more regimes.

            This function populates the following member variables:
            sc_start: lowest index of reliable superconducting branch
            sc_end: highest index of reliable superconducting branch + 1
            sci_start: lowest index of reliable science TES IV curve
            sci_end: highest index of reliable science TES IV curve + 1
            lab_start: lowest index of reliable lab curve
            lab_end: highest index of reliable lab branch + 1
            (+1s are so that you can use `data[start:end]` to get all the data)
            (also self.idx_arr which is just a list of all the above in that order)

            If a regime is not found, its start will be equal to its end so when you index you'll get an empty array.
            Is that the best way to do it? no idea.

            Plus the member variables that the original IVCurveAnalyzeSingle would have,
            but with slightly different (mostly compatible) definitions:
            sc_idx = sci_start to ensure that all the data inside the IV curve is valid. The original methods
              will struggle with the superconducting branch if there's an unstable region between the transition
              and superconducting, but at least they should be able to get the transition right.
            turn_idx = point in region [sci_start, sci_end) where dy/dx=0
            normal_idx = (sci_end + turn_idx)/2  (halfway between turn index and end of good normal branch)
         
        """
        x = self.x_raw
        y = self.y_raw
        idx_arr = np.zeros(6,dtype=int)
        # keep x in descending order for now
        if not x[1]-x[0] < 0:
            x = x[::-1]
            y = y[::-1]
        # determine IV polarity. if negative, flip
        b = len(x)
        pval = np.ma.polyfit(x[b-10:b],y[b-10:b],1)
        if pval[0] < 0: y=y*-1

        #attempt to find the superconducting branch
        idx_arr[1] = find_good_start(x,y,self.sc_r)
        idx_arr[0] = len(x) # I think this is a good assumption.
        #remember these arrays are still reversed, so the indices go backwards
        
        # attempt to find the normal branch
        sci_end = idx_arr[3] = find_good_start(x,y,self.normal_r_sci)

        # find the end of the science transition?? 
        # Science transition can have VERY LARGE negative change in dynamic resistance,
        # so we're mostly looking for a place where the change in dynamic resistance goes positive again.
        idx_arr[2] = find_bad(x,y,(-500,1),n_bad_size=4,start=sci_end,bad_frac=0.1)
            
        # attempt to find the lab normal branch
        idx_arr[5] = find_good_start(x,y,self.normal_r_lab)
        
        # find the end of the lab transition 
        idx_arr[4] = find_bad(x,y,(-1,1))

        self.x = x[::-1]
        self.y = y[::-1]
        self.idx_arr = len(x)-idx_arr
        self.sc_start = self.idx_arr[0]
        self.sc_end = self.idx_arr[1]
        self.sci_start =self.idx_arr[2]
        self.sci_end = self.idx_arr[3]
        self.lab_start = self.idx_arr[4]
        self.lab_end = self.idx_arr[5]

        self.sc_idx=max(self.sc_end-2,0)
        try:
            self.turn_idx = np.argmin(np.abs(np.diff(self.y[self.sc_idx:self.sci_end]))) + self.sc_idx
        except ValueError:
            self.turn_idx = self.sci_end
        self.normal_idx = (self.sci_end+self.turn_idx)//2

        try:
            self.lab_turn_idx = np.argmin(np.abs(np.diff(self.y[self.lab_start:self.lab_end]))) + self.lab_start
        except ValueError:
            self.lab_turn_idx = self.sci_end
        self.lab_normal_idx = (self.lab_end+self.lab_turn_idx)//2
        if plot:
            self.iv_regions_debug_plot()
        if self.target_lab:
            self.good_idxs[1]=self.lab_end
            self.good_idxs[0]=self.lab_start
            self.normal_idx = self.lab_normal_idx
            self.turn_idx= self.lab_turn_idx
            self.sc_idx = 0
        else:
            self.good_idxs[0]=0
            self.good_idxs[1]=self.sci_end


        return self.x, self.y

    def iv_regions_debug_plot(self):
        fig,axs = plt.subplots(2,1,sharex=True)
        axs[0].plot(self.x,self.y,label="IV data")
        axs[0].plot(self.x[[self.sc_idx,self.turn_idx,self.normal_idx]], self.y[[self.sc_idx,self.turn_idx,self.normal_idx]], '.')
        axs[0].set_ylabel("SQ1 FB [DAC]")
        axs[1].plot(self.x[1:],np.diff(self.y)/np.diff(self.x),'.',label="dI/dX")
        axs[1].plot(self.x[2:],np.diff(np.diff(self.y))/np.diff(self.x)[1:],'.',label="d2I/dx")
        axs[1].set_xlabel("TES bias [DAC]")
        for ax in axs:
            ax.axvspan(xmin=self.x[self.sc_start],xmax=self.x[max(self.sc_end-1,0)],alpha=0.1,color="C2",label="superconducting")
            ax.axvspan(xmin=self.x[self.sci_start],xmax=self.x[max(self.sci_end-1,0)],alpha=0.1,color="C3", label="science TES")
            ax.axvspan(xmin=self.x[self.lab_start],xmax=self.x[max(self.lab_end-1,0)],alpha=0.1,color="C4", label="lab TES")
            ax.legend()

    def remove_dc_offset(self,x,y,plot=False,r_n_override=None):
        """
        r_n_override should override the science tes
        find the correct DC offset for the Lab TES and then call the original method to do the rest

        args: x,y please just pass in self.x and self.y... I'd remove the args if it wasn't certain to break something else somewhere
        """
        assert self.x is x, "If you want to analyze other data make another object"
        
        
        if self.lab_start != self.lab_end:      
            # a lab branch does exist, so let's [attempt to] correct its offset 

            # Linear fit the normal branch of the lab transition
            p_lab = np.polyfit(x[self.lab_normal_idx:self.lab_end],y[self.lab_normal_idx:self.lab_end],1)

            #Subtract the linear fit's y-intercept
            y[self.lab_start:self.lab_end] -= p_lab[1]
            self.p_lab = p_lab
        else:
            self.p_lab = None
        try:
            y = super().remove_dc_offset(x,y,plot=False,r_n_override=r_n_override) # We'll do our own plotting to incorporate the extra information here
            #If we call super()remove, it WILL define self.p_norm and self.p_sc, but they might be NONe
        except TypeError:
            self.p_norm = None
            self.p_sc = None
        
            
        if plot:
            self.dc_subtraction_debug_plot(x,y)
        return y

    def dc_subtraction_debug_plot(self,x=None,y=None):
        x = x or self.x
        y = y or self.y
        fig,ax=plt.subplots()
        ax.plot(x,y,label="DC-subtracted IV data")
        p_norm = self.p_norm
        p_sc = self.p_sc
        p_lab = self.p_lab
        if p_norm is not None:
            ax.plot(x, p_norm[0]*x, '--', label="Science TES Normal")

        if p_sc is not None:
            ax.plot(x, p_sc[0]*x, '--', label="Superconducting")

        if p_lab is not None:
            ax.plot(x, p_lab[0]*x, '--', label="Lab TES normal")

        ax.legend()


class IVvsADRTempDual(IVversusADRTempOneRow):
    def __init__(
        self,
        dac_values,
        fb_values_arr,
        temp_list_k,
        iv_circuit,
        normal_r_sci,
        normal_r_lab,
        sc_r,
        state_list=None,
        figtitle=None,
        normal_resistance_fractions=[0.6,0.7,0.8,0.9],
        target_lab=False # set to True if you want to analyze the lab transition
    ):
        """Sorry but this initialization function will be duplicating a lot from IVversusADR and IVsetAnalyzeRow
        Mostly because I need to change one line from IVsetAnalyzeRow
        I can either redefine all those classes, or just make one franken-init function
        """

        ###### First half of __init__() of IVvsADR ######
        self.temp_list_k = temp_list_k
        self.rn_fracs = normal_resistance_fractions
        self.num_rn_fracs = len(self.rn_fracs)
        temp_list_k_str = []
        for ii in range(len(temp_list_k)):
            temp_list_k_str.append(str(temp_list_k[ii]))
        
        ###### Copied from IVSetAnalyzeRow.__init__() ######
        self.n_normal_pts = 10
        self.use_ave_offset = False
        self.ivs = []

        self.figtitle = figtitle
        self.dacs = dac_values
        self.fb_raw = fb_values_arr
        self.state_list = state_list
        self.n_dac_values, self.num_sweeps = np.shape(self.fb_raw)
        self.iv_circuit = iv_circuit

        for ii in range(self.num_sweeps):
            self.ivs.append(IVAnalyzeDual(
                self.dacs,
                self.fb_raw[:,ii],
                iv_circuit.rsh_ohm,
                normal_r_sci,
                normal_r_lab,
                sc_r,
                rx_ohm=iv_circuit.rx_ohm,
                to_i_bias=iv_circuit.to_i_bias,
                to_i_tes=iv_circuit.to_i_tes,
                target_lab=target_lab
            ))
        self.fb_align, self.v, self.i, self.p, self.r = self._package_iv_globals_(self.ivs)

        ###### Second half of IVvsADRTemp.__init() ######
        self.ro = self.r / self.r[0,:]
        self.ro_clean = self.ro.filled(fill_value=np.nan)
        self.ro_clean[0,:]=np.nan
        # self.v_clean, self.i_clean, self.p_clean, self.r_clean, _ = self.remove_bad_data(self.v,self.i,self.p,self.r,threshold=1)
        # self.ro_clean = self.r_clean / self.r_clean[0,:] # 0th bias index is highest bias, assume detector is normal there
        self.p_clean = self.p.filled(fill_value=np.nan)
        self.i_clean = self.i.filled(fill_value=np.nan)
        self.v_clean = self.v.filled(fill_value=np.nan)
        self.r_clean = self.r.filled(fill_value=np.nan)

        # for p in self.p_clean.T:
        #     print(np.all(np.isnan(p)))
        #print(self.p_clean.shape, self.ro_clean.shape)
        self.p_at_rnfrac = self.get_value_at_rn_frac(self.rn_fracs,self.p_clean,self.ro_clean)

        self.pfits = self.fit_pvt_for_all_rn_frac()


    def _package_iv_globals_(self,ivs):
        """
        Make all the data from individual IVCurveAnalyzeSingle objects into arrays
        """
        lab_tes = ivs[0].target_lab
        v_tes = np.ma.zeros((ivs[0].y.shape[0], len(ivs)))
        i_tes = np.ma.zeros_like(v_tes)
        p_tes = np.ma.zeros_like(v_tes)
        r_tes = np.ma.zeros_like(v_tes)
        fb = np.ma.zeros_like(v_tes)
        for i,iv in enumerate(ivs):
            if lab_tes:
                a = iv.lab_start
                b = iv.lab_end
            else:
                a,b = iv.good_idxs
                a = iv.sci_start
            i1 = v_tes.shape[0]-b
            i2 = v_tes.shape[0]-a-1
            
            v_tes[:,i] = iv.v_tes[::-1] # I'm not *exactly* sure why we're reversing these arrays, but ok
            i_tes[:,i] = iv.i_tes[::-1] # values now DECREASING with increasing index, like in the raw data.
            p_tes[:,i] = iv.p_tes[::-1]
            r_tes[:,i] = iv.r_tes[::-1]
            fb[:,i] = iv.y[::-1]

            v_tes[:i1,i]=np.ma.masked
            v_tes[i2:,i]=np.ma.masked
            i_tes[:i1,i]=np.ma.masked
            i_tes[i2:,i]=np.ma.masked
            p_tes[:i1,i]=np.ma.masked
            p_tes[i2:,i]=np.ma.masked
            r_tes[:i1,i]=np.ma.masked
            r_tes[i2:,i]=np.ma.masked
            fb[:i1,i]=np.ma.masked
            fb[i2:,i]=np.ma.masked
            r_tes[0,i] = iv.rn # WHATEVER I AM GETTING FED UP
        return fb, v_tes, i_tes, p_tes, r_tes

    @classmethod
    def from_iv_temp_sweep_data(cls, temp_sweep_data, row, normal_r_sci, normal_r_lab, sc_r,  **kwargs):
        """Kwargs can be:
            * temp_cut: data points with T>temp_cut will be discarded
            * normal_resistance_fractions (default [0.8,0.9])
            * figtitle (Default None) 
            * use_IVCurveAnalyzeSingle (Default True)
        """
        tsd=temp_sweep_data
        temp_list_k = tsd.set_temps_k
        fb_values_arr = []
        dac_values = tsd.data[0].dac_values
        for ivcd in tsd.data:
            raw_fb_arr = np.array(ivcd.fb_values)
            fb_values_arr.append(raw_fb_arr[:,row])
        fb_values_arr = np.array(fb_values_arr)
        iv_circuit = detchar.iv_data.make_iv_circuit(tsd.data[0].extra_info)
        try:
            temp_cut = kwargs["temp_cut"]
            tempr_arr = np.array(temp_list_k)
            flag_arr = tempr_arr <= temp_cut
            temp_list_k = list(tempr_arr[flag_arr])
            fb_values_arr = fb_values_arr[flag_arr]
            kwargs.pop("temp_cut")
        except KeyError:
            pass
        return cls(
            dac_values, 
            fb_values_arr.T, 
            temp_list_k, 
            iv_circuit,
            normal_r_sci,
            normal_r_lab,
            sc_r,
            **kwargs
        )
