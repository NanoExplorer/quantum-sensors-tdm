from dataclasses import dataclass
import dataclasses
from dataclasses_json import dataclass_json
from typing import Any, List
import numpy as np
import pylab as plt
import collections
import os
from numpy.polynomial.polynomial import Polynomial

# iv data classes -----------------------------------------------------------------------------
@dataclass_json
@dataclass
class IVCurveColumnData():
    nominal_temp_k: float
    pre_temp_k: float
    post_temp_k: float
    pre_time_epoch_s: float
    post_time_epoch_s: float
    pre_hout: float
    post_hout: float
    post_slope_hout_per_hour: float
    dac_values: List[int]
    fb_values: List[Any] = dataclasses.field(repr=False) #actually a list of np arrays
    bayname: str
    db_cardname: str
    column_number: int
    extra_info: dict
    pre_shock_dac_value: float

    def plot(self):
        plt.figure()
        plt.plot(self.dac_values, self.fb_values)
        plt.xlabel("dac values (arb)")
        plt.ylabel("fb values (arb)")
        plt.title(f"bay {self.bayname}, db_card {self.db_cardname}, nominal_temp_mk {self.nominal_temp_k*1000}")

    def to_file(self, filename, overwrite = False):
        if not overwrite:
            assert not os.path.isfile(filename)
        with open(filename, "w") as f:
            f.write(self.to_json())

    @classmethod
    def from_file(cls, filename):
        with open(filename, "r") as f:
            return cls.from_json(f.read())

    def fb_values_array(self):
        return np.vstack(self.fb_values)

    def xy_arrays_zero_subtracted_at_origin(self):
        dac_values = np.array(self.dac_values)
        dac_zero_ind = np.where(dac_values==0)[0][0]
        fb = self.fb_values_array()
        fb -= fb[dac_zero_ind, :]

        return dac_values, fb

    def xy_arrays_zero_subtracted_at_normal_y_intercept(self, normal_above_fb):
        dac_values = np.array(self.dac_values)
        fb = self.fb_values_array()
        for i in range(fb.shape[1]):
            fb[:,i] = fit_normal_zero_subtract(dac_values, fb[:, i], normal_above_fb)
        return dac_values, fb

    def xy_arrays_zero_subtracted_at_dac_high(self):
        dac_values = np.array(self.dac_values)
        fb = self.fb_values_array()
        fb = fb - fb[0,:]
        return dac_values, fb

    def xy_arrays(self):
        dac_values = np.array(self.dac_values)
        fb = self.fb_values_array()
        for i in range(fb.shape[1]):
            fb[:,i] = fb[:, i]
        return dac_values, fb

def fit_normal_zero_subtract(x, y, normal_above_x):
    normal_inds = np.where(x>normal_above_x)[0]
    pfit_normal = Polynomial.fit(x[normal_inds], y[normal_inds], deg=1)
    normal_y_intersect = pfit_normal(0)
    return y-normal_y_intersect

@dataclass_json
@dataclass
class IVTempSweepData():
    set_temps_k: List[float]
    data: List[IVCurveColumnData]

    def to_file(self, filename, overwrite = False):
        if not overwrite:
            assert not os.path.isfile(filename)
        with open(filename, "w") as f:
            f.write(self.to_json())

    @classmethod
    def from_file(cls, filename):
        with open(filename, "r") as f:
            return cls.from_json(f.read())

    def plot_row(self, row, zero="dac high"):
        plt.figure()
        for curve in self.data:
            if zero == "origin":
                x, y = curve.xy_arrays_zero_subtracted_at_origin()
            elif zero == "fit normal":
                x, y = curve.xy_arrays_zero_subtracted_at_normal_y_intercept(normal_above_fb=25000)
            elif zero == "dac high":
                x, y = curve.xy_arrays_zero_subtracted_at_dac_high()
            t_mK = curve.nominal_temp_k*1e3
            dt_mK = (curve.post_temp_k-curve.pre_temp_k)*1e3
            plt.plot(x, y[:,row], label=f"{t_mK:0.2f} mK, dt {dt_mK:0.2f} mK")
        plt.xlabel("dac value (arb)")
        plt.ylabel("feedback (arb)")
        plt.title(f"row={row} bayname {curve.bayname}, db_card {curve.db_cardname}, zero={zero}")
        plt.legend()

@dataclass_json
@dataclass
class IVColdloadSweepData(): #set_cl_temps_k, pre_cl_temps_k, post_cl_temps_k, data
    set_cl_temps_k: List[float]
    data: List[IVTempSweepData]
    extra_info: dict

    def to_file(self, filename, overwrite = False):
        if not overwrite:
            assert not os.path.isfile(filename)
        with open(filename, "w") as f:
            f.write(self.to_json())

    @classmethod
    def from_file(cls, filename):
        with open(filename, "r") as f:
            return cls.from_json(f.read())

    def plot_row(self, row):
        #n=len(set_cl_temps_k)
        #plt.figure()
        for ii, tempSweep in enumerate(self.data): # loop over IVTempSweepData instances (ie coldload temperature settings)
            for jj, set_temp_k in enumerate(tempSweep.set_temps_k): # loop over bath temperatures
                data = tempSweep.data[jj]
                x = data.dac_values ; y=data.fb_values_array()
                plt.plot(x,y[:,row],label='T_cl = %.1fK; T_b = %.1f'%(self.set_cl_temps_k[ii],data.nominal_temp_k))
        plt.xlabel("dac value (arb)")
        plt.ylabel("feedback (arb)")
        plt.title(f"row={row} bayname {data.bayname}, db_card {data.db_cardname}")
        plt.legend()

@dataclass_json
@dataclass
class IVCircuit():
    rfb_ohm: float # feedback resistor
    rbias_ohm: float # bias resistor
    rsh_ohm: float # shunt resistor
    rx_ohm: float # parasitic resistance in series with TES
    m_ratio: float # ratio of feedback mutual inductance to input mutual inductance
    vfb_gain: float # volts/arbs of feeback (14 bit dac)
    vbias_gain: float # volts/arbs of bias (16 bit dac for blue boxes)

    def iv_raw_to_physical_fit_rpar(self, vbias_arbs, vfb_arbs, sc_below_vbias_arbs):
        ites0, vtes0 = self.iv_raw_to_physical(vbias_arbs, vfb_arbs, rpar_ohm=0)
        sc_inds = np.where(vbias_arbs<sc_below_vbias_arbs)[0]
        pfit_sc = Polynomial.fit(ites0[sc_inds], vtes0[sc_inds], deg=1)
        rpar_ohm = pfit_sc.deriv(m=1)(0)
        return ites0, vtes0-ites0*rpar_ohm, rpar_ohm

    def iv_raw_to_physical_simple(self, vbias_arbs, vfb_arbs, rpar_ohm):
        #assume rbias >> rshunt
        ifb = vfb_arbs*self.vfb_gain / self.rfb_ohm # feedback current
        ites = ifb / self.m_ratio # tes current
        ibias = vbias_arbs*self.vbias_gain/self.rbias_ohm # bias current
        # rtes = rsh_ohm + rpar_ohm - ibias*rsh_ohm/ites
        vtes = (ibias-ites)*self.rsh_ohm-ites*rpar_ohm
        return ites, vtes

    def to_physical_units(self,dac_values,fb_array):
        y = fb_array*self.vfb_gain *(self.rfb_ohm*self.m_ratio)**-1
        I = dac_values*self.vbias_gain/self.rbias_ohm # current sent to TES bias network
        n,m = np.shape(y)
        x = np.zeros((n,m))
        for ii in range(m):
            #x[:,ii] = I*self.rsh_ohm - y[:,ii]*(self.rsh_ohm+self.rx_ohm[ii]) # for future for unique rx per sensor
            x[:,ii] = I*self.rsh_ohm - y[:,ii]*(self.rsh_ohm+self.rx_ohm)
        return x,y

### polcal data classes ---------------------------------------------------------------------

@dataclass_json
@dataclass
class PolCalSteppedSweepData():
    angle_deg_req: List[float]
    angle_deg_meas: List[float]
    iq_v_angle: List[Any] = dataclasses.field(repr=False) #actually a list of np arrays
    #iq_rms_values: List[Any] = dataclasses.field(repr=False) #actually a list of np arrays
    row_order: List[int]
    #bayname: str
    #db_cardname: str
    column_number: int
    source_amp_volt: float
    source_offset_volt: float
    source_frequency_hz: float
    #nominal_temp_k: float
    pre_temp_k: float
    post_temp_k: float
    pre_time_epoch_s: float
    post_time_epoch_s: float
    extra_info: dict

    def to_file(self, filename, overwrite = False):
        if not overwrite:
            assert not os.path.isfile(filename)
        with open(filename, "w") as f:
            f.write(self.to_json())

    @classmethod
    def from_file(cls, filename):
        with open(filename, "r") as f:
            return cls.from_json(f.read())

    def plot(self, rows_per_figure=None):
        ''' rows_per_figure is a list of lists to group detector responses
            to be plotted together.  If None will plot in groups of 8.
        '''
        if rows_per_figure is not None:
            pass
        else:
            num_in_group = 8
            n_angles,n_rows,n_iq = np.shape(self.iq_v_angle)
            n_groups = n_rows//num_in_group + 1
            rows_per_figure=[]
            for jj in range(n_groups):
                tmp_list = []
                for kk in range(num_in_group):
                    row_index = jj*num_in_group+kk
                    if row_index>=n_rows: break
                    tmp_list.append(row_index)
                rows_per_figure.append(tmp_list)
        for ii,row_list in enumerate(rows_per_figure):
            fig,ax = plt.subplots(3,num=ii)
            for row in row_list:
                ax[0].plot(self.angle_deg_meas,self.iq_v_angle[:,row,0],'o-',label=row)
                ax[1].plot(self.angle_deg_meas,self.iq_v_angle[:,row,1],'o-',label=row)
                ax[2].plot(self.angle_deg_meas,np.sqrt(self.iq_v_angle[:,row,0]**2+self.iq_v_angle[:,ii,1]**2),'o-',label=row)
            ax[0].set_ylabel('I (DAC)')
            ax[1].set_ylabel('Q (DAC)')
            ax[2].set_ylabel('Amplitude (DAC)')
            ax[2].set_xlabel('Angle (deg)')
            ax[1].legend()
            ax[0].set_title('Column %d, Group %d'%(self.column_number,ii))
        plt.show()

@dataclass_json
@dataclass
class PolCalSteppedBeamMapData():
    xy_position_list: List[Any]
    data: List[PolCalSteppedSweepData]

@dataclass_json
@dataclass
class SineSweepData():
    frequency_hz: List[Any]
    iq_data: List[Any] = dataclasses.field(repr=False)
    amp_volt: float
    offset_volt: float
    row_order: List[int]
    column_str: str
    signal_column_index: int
    reference_column_index: int
    number_of_lockin_periods: int
    pre_temp_k: float
    post_temp_k: float
    pre_time_epoch_s: int
    post_time_epoch_s: int
    extra_info: dict

    def to_file(self, filename, overwrite = False):
        if not overwrite:
            assert not os.path.isfile(filename)
        with open(filename, "w") as f:
            f.write(self.to_json())

    @classmethod
    def from_file(cls, filename):
        with open(filename, "r") as f:
            return cls.from_json(f.read())

    def plot(self,fignum=1):
        fig, ax = plt.subplots(nrows=2,ncols=2,sharex=False,figsize=(12,8),num=fignum)
        n_freq,n_row,foo = np.shape(self.iq_v_freq)
        for ii in range(n_row):
            ax[0][0].plot(self.freq_hz,self.iq_v_freq[:,ii,0],'o-')
            ax[0][1].plot(self.freq_hz,self.iq_v_freq[:,ii,1],'o-')
            ax[1][0].plot(self.freq_hz,self.iq_v_freq[:,ii,0]**2+self.iq_v_freq[:,ii,1]**2,'o-')
            ax[1][1].plot(self.freq_hz,np.arctan(self.iq_v_freq[:,ii,1]/self.iq_v_freq[:,ii,0]),'o-')

        # axes labels
        ax[0][0].set_ylabel('I')
        ax[0][1].set_ylabel('Q')
        ax[1][0].set_ylabel('I^2+Q^2')
        ax[1][1].set_ylabel('Phase')
        ax[1][0].set_xlabel('Freq (Hz)')
        ax[1][1].set_xlabel('Freq (Hz)')

        ax[1][1].legend(self.row_order)

@dataclass_json
@dataclass
class CzData():
    data: List[Any]
    detector_bias_list: List[int]
    temp_list_k: List[float]
    db_cardname: str
    db_tower_channel_str: str
    temp_settle_delay_s: float
    extra_info: dict

    def to_file(self, filename, overwrite = False):
        if not overwrite:
            assert not os.path.isfile(filename)
        with open(filename, "w") as f:
            f.write(self.to_json())

    @classmethod
    def from_file(cls, filename):
        with open(filename, "r") as f:
            return cls.from_json(f.read())
