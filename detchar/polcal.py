''' polcal.py

    Polarization calibration software using aerotech XY stage, velmex stepper motor controlled wire grid,
    function generator biased IR source, and NIST `previous generation (TDM) electronics'

    @author JH 7/2021, based on Jay's software for legacy electronics.
'''

from dataclasses import dataclass
import dataclasses
from dataclasses_json import dataclass_json
from typing import Any, List

from nasa_client import EasyClient
from instruments import BlueBox, Velmex, Agilent33220A, AerotechXY
from adr_gui.adr_gui_control import AdrGuiControl

import time
import numpy as np
import pylab as plt
import progress.bar
import os
from tools import SoftwareLockinAcquire

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
                ax[0].plot(self.angle_deg,self.iq_v_angle[:,row,0],'o-',label=row)
                ax[1].plot(self.angle_deg,self.iq_v_angle[:,row,1],'o-',label=row)
                ax[2].plot(self.angle_deg,np.sqrt(self.iq_v_angle[:,row,0]**2+self.iq_v_angle[:,ii,1]**2),'o-',label=row)
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

class PolcalSteppedSweep():
    ''' Acquire polcal at stepped, fixed absolute angles '''
    def __init__(self, angle_deg_list,
                 source_amp_volt=3.0, source_offset_volt=1.5, source_frequency_hz=5.0,
                 num_lockin_periods = 10,
                 row_order=None,
                 grid_motor=None,
                 initialize_grid_motor=True):

        # hardware and class initialization
        self.sla = SoftwareLockinAcquire(easy_client=None, signal_column_index=0,reference_column_index=1,
                                         signal_feedback_or_error='feedback',num_pts_per_period=None)
        self.source = Agilent33220A()
        self.adr_gui_control = AdrGuiControl() #self._handle_adr_gui_control_arg(adr_gui_control)
        self.init_source(source_amp_volt, source_offset_volt, source_frequency_hz)
        self.grid_motor = self._handle_grid_motor_arg(grid_motor,initialize_grid_motor)

        # input parameters
        self.angles = self._handle_angle_arg(angle_deg_list)
        self.num_angles = len(self.angle_deg)
        self.source_amp_v = source_amp_volt
        self.source_offset_v = source_offset_volt
        self.source_freq_hz = source_frequency_hz
        self.num_lockin_periods = num_lockin_periods
        self.waittime_s = 0.1 # time to wait between setting grid angle and acquiring data

        self.row_order = self._handle_row_to_state(row_order)

    def _handle_grid_motor_arg(self,grid_motor,initialize_grid_motor):
        if grid_motor is not None:
            return grid_motor
        else:
            return Velmex(doInit=initialize_grid_motor)

    def _handle_row_to_state(self,row_order):
        if row_order is not None:
            return row_order
        return list(range(self.sla.ec.nrow))

    def _handle_angle_arg(self,angle_deg_list):
        ''' velmex motor has finite resolution, so map angle_deg_list to this
            resolution.
        '''
        for angle in angle_deg_list:
            self.grid_motor.check_angle_safe(angle) # ensure IR source wires not over-twisted
        return self.grid_motor.angle_list_to_stepper_resolution(angle_deg_list)

    def init_source(self, amp, offset, frequency):
        #self.source.SetFunction(function = 'sine')
        self.source.SetFunction(function = 'square')
        self.source.SetLoad('INF')
        self.source.SetFrequency(frequency)
        self.source.SetAmplitude(amp)
        self.source.SetOffset(offset)
        self.source.SetOutput(outputstate='on')

    def get_point(self,window=False):
        return self.sla.getData(num_periods=self.num_lockin_periods, window=window,debug=False)

    def get_polcal(self, extra_info = {}, move_to_zero_at_end = True):
        pre_time = time.time()
        pre_temp_k = self.adr_gui_control.get_temp_k()

        iq_v_angle = np.empty((self.num_angles,self.sla.ec.nrow,2))
        measured_angles = []
        for ii, angle in enumerate(self.angles):
            print('Moving grid to angle = %.2f deg'%(angle)
            self.grid_motor.move_absolute(angle,wait=True)
            m_angle = self.grid_motor.get_current_position()
            measured_angles.append(m_angle)
            print('Motor at angle = ',m_angle)
            time.sleep(self.waittime_s)
            iq_arr = self.get_point() # nrow x 2 array
            iq_v_angle[ii,:,:] = iq_arr
        post_temp_k = self.adr_gui_control.get_temp_k()
        post_time = time.time()

        print('Acquisition complete.')
        if move_to_zero_at_end:
            print('Unwinding wires; moving to angle=0')
            self.grid_motor.move_to_zero_index(wait=True)

        return PolCalSteppedSweepData(angle_deg_req=self.angle_deg,
                                      angle_deg_meas=measured_angles,
                                      iq_v_angle = iq_v_angle,
                                      row_order=self.row_order,
                                      #bayname=self.bayname,
                                      #db_cardname=self.db_cardname,
                                      column_number=0,
                                      source_amp_volt=self.source_amp_v,
                                      source_offset_volt=self.source_offset_v,
                                      source_frequency_hz=self.source_freq_hz,
                                      pre_temp_k=pre_temp_k,
                                      post_temp_k=post_temp_k,
                                      pre_time_epoch_s=pre_time,
                                      post_time_epoch_s=post_time,
                                      extra_info=extra_info)

class PolCalSteppedBeamMap():
    ''' Acquire PolcalSteppedSweep for x,y positions '''
    def __init__(self,xy_position_list, polcal_stepped_sweep, doXYinit=True):
        self.pcss = polcal_stepped_sweep
        self.xy_pos_list = xy_position_list
        self.x_velocity_mmps = self.y_velocity_mmps = 25 # velocity of xy motion in mm per s
        self.xy = AerotechXY() #
        if doXYinit:
            self.xy.initialize()

    def acquire(self, extra_info = {}):
        data_list = []
        for ii, xy_pos in enumerate(self.xy_pos_list):
            self.xy.move_absolute(xy_pos[0],xy_pos[1],self.x_velocity_mmps,self.y_velocity_mmps)
            data_list.append(self.pcss.get_polcal(extra_info = extra_info))
        return PolCalSteppedBeamMapData(xy_position_list = self.xy_pos_list, data=data_list)

if __name__ == "__main__":
    angles = list(range(0,360,10))
    pcss = PolcalSteppedSweep(angle_deg_list=angles)
    pc_data = pcss.get_polcal()
    pc_data.to_file('test_polcal_data',overwrite=True)
    pc_data.plot()
