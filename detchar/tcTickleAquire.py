#! /usr/bin/env python
''' tcTickleAquire.py
based on ivCurveAcquire and iv_utils.tc_tickle
top-level script to acquire an iv curve data set.
usage:
./tcTickleAquire.py <config_file> <description>

@author JH 
v0: 2/2021
v1: 4/2021 updated to allow plotting and to take IV curve at current temperature if 
@author GCJ
v0 5/2022 can acquire and store RvT data, can't control ramp rate just yet fixed to 50mK/min in adr_gui_control or somewhere
Update: 2026: CR has added ramp rate controls to the "advanced" settings button in adr_gui. Note that unless this is REALLY SMALL
the actual ADR temperature won't change linearly with time due to the PID loop's response time.

'''

import yaml, sys, os
from iv_utils import *
from IPython import embed
import pickle
from acquire import column_name_to_num

def plot_rvt_groups(data):
    t = data['temperature']
    fbs = data['feedback']
    plt.plot(t,fbs)
    plt.xlabel('Temperature (K)')
    plt.ylabel('Feedback')
    plt.show()
    return

def create_filename(cfg):
    baystring = 'Column' + cfg['detectors']['Column']
    if not os.path.exists(cfg['io']['RootPath']):
        print('The path: %s does not exist! Making directory now.'%cfg['io']['RootPath'])
        os.makedirs(cfg['io']['RootPath'])
    localtime=time.localtime()
    thedate=str(localtime[0])+'%02i'%localtime[1]+'%02i'%localtime[2]
    etime = str(time.time()).split('.')[0]
    filename = cfg['io']['RootPath']+cfg['detectors']['DetectorName']+'_'+baystring+'_rvt_'+thedate+'_'+etime
    write_filename = filename+'.pkl'
    return write_filename

if __name__=='__main__':
    n_args = len(sys.argv)
    config_filename = str(sys.argv[1])
    if n_args > 2:
        desc = str(sys.argv[2])
    else:
        desc=''
    
    # open config file
    with open(config_filename, 'r') as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
    write_filename = create_filename(cfg)

    if cfg['voltage_bias']['source'] in ['bluebox','BlueBox','Blue Box','blue box']:
        voltage_source = 'bluebox'
    else:
        voltage_source = None

    print(voltage_source)
    bath_temps = cfg['runconfig']['bathTemperatures']
    if not len(bath_temps)==2:
        print('Need 2 bath temperatures in cfg. Exiting')
        sys.exit()
    Tstart, Tstop = bath_temps   

    dac0 = int(cfg['voltage_bias']['v_stop_dac'])
    dac1 = int(cfg['voltage_bias']['v_start_dac'])
    print(dac0,dac1)
    #############
    pt_taker = IVPointTaker(db_cardname=cfg['voltage_bias']['db_cardname'], bayname=column_name_to_num(cfg['detectors']['Column']), voltage_source = voltage_source)
    curve_taker = IVCurveTaker(pt_taker, temp_settle_delay_s=cfg['runconfig']['temp_settle_delay_s'], shock_normal_dac_value=65000, zero_tower_at_end=cfg['voltage_bias']['setVtoZeroPostIV'])
    curve_taker.prep_fb_settings(I=cfg['dfb']['i'], fba_offset=cfg['dfb']['dac_a_offset'], ARLoff=True)

    t = []
    fbs = []
    curve_taker.set_temp_and_settle(Tstart) # uses temp_settle_delay_s, but might not be long enough

    print('Checking if we are at Tstart={:.3f} K.'.format(Tstart))
    Tnow = pt_taker.adr.get_temp_k()
    while not np.isclose(Tnow,Tstart,atol=1E-3):        
        time.sleep(1)
        Tnow = pt_taker.adr.get_temp_k()

    print('We are at Tstart={:.3f} K, moving to Tstop={:.3f} K now.'.format(Tstart,Tstop))
    old_ramp_rate = pt_taker.adr.get_ramp_rate_kpm() # note old ramp rate so we go back to it when done
    try:
        pt_taker.adr.set_ramp_rate_kpm(cfg["runconfig"]["ramprate"])
    except KeyError:
        print("No ramp rate specified in config, leaving as-is")
    pt_taker.adr.set_temp_k(Tstop) # no delay, just gooo

    Tnow = pt_taker.adr.get_temp_k()

    while not np.isclose(Tnow,Tstop,atol=1E-3): # Note this means we stop 1 mK early
        try:
            Tnow = pt_taker.adr.get_temp_k()
            t.append(Tnow)
            fb0 = curve_taker.pt.get_iv_pt(dac0)
            fb1 = curve_taker.pt.get_iv_pt(dac1)
            fbs.append(fb1-fb0)
        except:
            break 
    print('Finished. We are at Tstop={:.3f} K now.'.format(Tstop))

    data = {'temperature':t,
            'feedback':fbs,
            'Tstart':Tstart,
            'Tstop':Tstop,
            'dac0':dac0,
            'dac1':dac1,
            'desc':desc,
            'cfg':cfg,
            }
    pt_taker.adr.set_ramp_rate_kpm(old_ramp_rate)
    if cfg['runconfig']['show_plot']:
        print('showing plot')
        plot_rvt_groups(data)

    if cfg['runconfig']['save_data']:
        #data.to_file(write_filename,overwrite=True)
        with open(write_filename,'wb') as opf:
            pickle.dump(data,opf)
        print('data aquistion finished.\nWrote to file:',write_filename)
    else:
        is_save = input('You have selected not to save data.  If you would like to save the file, hit 1 and enter.')
        if is_save=='1': 
            with open(write_filename,'wb') as opf:
                pickle.dump(data,opf)
            print('data aquistion finished.\nWrote to file:',write_filename)
        else:
            print('Exiting without saving')