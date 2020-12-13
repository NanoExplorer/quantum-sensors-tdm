#! /usr/bin/env python
'''
ivCurve.py
11/2020
@author JH

Script to take IV curves on a single column of detectors as a function of bath temperature. 
Assumes multiplexer is setup in cringe before running.
Must exit out of adr_gui  

usage:
./ivCurve.py <config_filename>

requirements:
iv configuration file
tower configuration file
pyYAML

to do:
DFB_CARD_INDEX
error handling: Tbath, v_bias
overbias
tesacquire used for unmuxed case. 
what to do about tesacquire, tesanalyze, sweeper, LoadMuxSettings, singleMuxIV 

'''

# standard python module imports
import sys, os, yaml, time, subprocess, re
import numpy as np
import matplotlib.pyplot as plt 

# # QSP written module imports
from cringe.cringe_control import CringeControl
from adr_system import AdrSystem
from instruments import BlueBox, Cryocon22  
import tespickle 
from nasa_client import EasyClient




##########################################################################################################
##########################################################################################################
##########################################################################################################

def findThisProcess( process_name ):
    ps = subprocess.Popen("ps -eaf | grep "+process_name, shell=True, stdout=subprocess.PIPE)
    output = ps.stdout.read()
    ps.stdout.close()
    ps.wait()
    return output

def isThisRunning( process_name ):
    output = findThisProcess( process_name )
    if re.search('path/of/process'+process_name, output) is None:
        return False
    else:
        return True

def getDataAverageAndCheck(ec,v_min=0.1,v_max=0.9,npts=10000,verbose=False):
    flag=False
    data = ec.getNewData(minimumNumPoints=npts,exactNumPoints=True,toVolts=True)
    data_mean = np.mean(data,axis=2)
    data_std = np.std(data,axis=2)

    if verbose:
        for ii in range(ec.ncol):
            for jj in range(ec.nrow):
                print('Col ',ii, 'Row ',jj, ': %0.4f +/- %0.4f'%(data_mean[ii,jj,1],data_std[ii,jj,1]))

    a = data_mean[:,:,1][data_mean[:,:,1]>v_max]
    b = data_mean[:,:,1][data_mean[:,:,1]<v_min]
    if a.size: 
        print('Value above ',v_max,' detected')
        # relock here
        flag=True
    if b.size:
        print('Value below ',v_min,' detected')
        # relock here
        flag=True

    # have some error handling about if std/mean > threshold

    return data_mean, flag

def iv_sweep(ec, vs, v_start=0.1,v_stop=0,v_step=0.01,sweepUp=False,showPlot=False,verbose=False,):
    ''' ec: instance of easy client
        vs: instance of bluebox (voltage source)
        v_start: initial voltage
        v_stop: final voltage
        v_step: voltage step size
        sweepUp: if True sweeps in ascending voltage
    '''
    v_arr = np.arange(v_stop,v_start+v_step,v_step)
    if not sweepUp:
        v_arr=v_arr[::-1]
    
    N=len(v_arr)
    data_ret = np.zeros((ec.ncol,ec.nrow,N,2))
    flags = np.zeros(N)
    for ii in range(N):
        vs.setvolt(v_arr[ii])
        data, flag = getDataAverageAndCheck(ec,verbose=verbose)
        data_ret[:,:,ii,:] = data
        flags[ii] = flag
    
    if showPlot:
        for ii in range(ec.ncol):
            plt.figure(ii)
            for jj in range(ec.nrow):
                plt.subplot(211)
                plt.plot(v_arr,data_ret[ii,jj,:,1])
                plt.xlabel('V_bias')
                plt.ylabel('V_fb')
                plt.subplot(212)
                plt.plot(v_arr,data_ret[ii,jj,:,0])
                plt.xlabel('V_bias')
                plt.ylabel('V_err')
        plt.show()
    return v_arr, data_ret, flags

def removeZerosIV(iv):
    ''' Removes the zeros put in by jump 
        Looking for bias voltage in iv[0,:] and fb voltage in iv[1,:] '''

    for pnt in range(len(iv[1])-1,0,-1):
        if iv[1,pnt] == 0:
            iv = np.hstack((iv[:,: pnt],iv[:,pnt+1 :]))
    return iv

def IsTemperatureStable(T_target,adr, Tsensor=1,tol=.005,time_out=180.):
    ''' determine if the servo has reached the desired temperature '''
    
    if time_out < 10:
        print('Time for potential equilibration must be longer than 10 seconds')
        return False
    
    cur_temp=adr.GetTemperature(Tsensor)
    it_num=0
    while abs(cur_temp-T_target)>tol:
        time.sleep(10.)
        cur_temp = adr.GetTemperature(Tsensor)
        print('Current Temp: ' + str(cur_temp))
        it_num=it_num+1
        if it_num>round(int(time_out/10.)):
            print('exceeded the time required for temperature stability: %d seconds'%(round(int(10*it_num))))
            return False
    return True

def overBias(adrTempControl,voltage_sweep_source,Thigh,Tb,Vbias=0.5,Tsensor=1):
    ''' raise Tbath above Tc, overbias bolometer, cool back to base temperature while 
        keeping bolometer in the normal state
    '''
    adrTempControl.SetTemperatureSetPoint(Thigh) # raise Tb above Tc
    ThighStable = IsTemperatureStable(Thigh,adrTempControl,Tsensor=Tsensor,tol=0.005,time_out=180.) # determine that it got to Thigh
    if ThighStable:
        print('Successfully raised Tb > %.3f.  Appling detector voltage bias and cooling back down.'%(Thigh))
    else:
        print('Could not get to the desired temperature above Tc.  Current temperature = ', adrTempControl.GetTemperature(Tsensor))
    #voltage_sweep_source.setvolt(2.5)
    #time.sleep(1.0)
    voltage_sweep_source.setvolt(Vbias) # voltage bias to stay above Tc
    adrTempControl.SetTemperatureSetPoint(Tb) # set back down to Tbath, base temperature
    TlowStable = IsTemperatureStable(Tb,adrTempControl,Tsensor=Tsensor,tol=0.002,time_out=180.) # determine that it got to Tbath target
    if TlowStable:
        print('Successfully cooled back to base temperature '+str(Tb))
    else:
        print('Could not cool back to base temperature'+str(Tb)+'. Current temperature = ', adrTempControl.GetTemperature(Tsensor))
    
def setupTemperatureController(adrTempControl, channel, t_set=0.1,heaterRange=100,heaterResistance=100.0):
    print('Setting up temperature controller to servo mode on channel',channel, 'and regulating to %.1f mK'%(t_set*1000))
    # determine what is the current state of temperature control
    mode = adrTempControl.getControlMode() # can be closed, open, off, or zone
    #cur_chan,autscan=adrTempControl.GetScan() # which channel is currently being read? 
    #cur_temp = adrTempControl.getTemperature(cur_chan) # read the current temperature from that channel
    #cur_tset = adrTempControl.getTemperatureSetPoint() # current temperature setpoint for controlling

    print('current mode: ',mode)

    if mode=='off':
        pass
        
    elif mode=='open':
        adrTempControl.SetManualHeaterOut(0)
        time.sleep(1)

    elif mode=='closed':
        adrTempControl.setTemperatureSetPoint(0) 

    adrTempControl.setupPID(exciterange=3.16e-9, therm_control_channel=channel, ramprate=0.05, heater_resistance=heaterResistance,heater_range=heaterRange,setpoint=t_set)

def convertToLegacyFormat(v_arr,data_ret,nrows,pd,tes_pickle,column,mux_rows,column_index=0):
    for ii in range(nrows):
        ivdata = np.vstack((v_arr, data_ret[column_index,ii,:,1])) # only return the feedback, not error
        iv_dict = tes_pickle.createIVDictHeater(ivdata, temperature=pd['temp'], feedback_resistance=pd['feedback_resistance'],
                                                heater_voltage=None,heater_resistance=None, 
                                                measured_temperature=pd['measured_temperature'],
                                                bias_resistance=pd['bias_resistance'])
        tes_pickle.addIVRun(column, mux_rows[ii], iv_dict)
        tes_pickle.savePickle()

def createIVDictBB_thermalization(ivdata,t_initial=None,\
                    #t_final=None,\
                    #t_total=None,\
                    bath_temperature_commanded=None,\
                    bath_temperature_measured=None,\
                    bb_temperature_commanded=None,\
                    bb_temperature_measured_before=None,\
                    bb_temperature_measured_after=None,\
                    bb_voltage_measured_before=None,\
                    bb_voltage_measured_after=None,\
                    feedback_resistance=None,\
                    bias_resistance=None,\
                    multiplexedIV=None):
    new_dict = {}
    new_dict['data'] = ivdata
    new_dict['datetime'] = time.localtime()
    new_dict['initial_measurement_time'] = t_initial
    #new_dict['final_measurement_time'] = t_final
    #new_dict['total_measurement_time'] = t_total
    new_dict['bath_temperature_commanded'] = bath_temperature_commanded
    new_dict['bath_temperature_measured'] = bath_temperature_measured
    new_dict['bb_temperature_commanded'] = bb_temperature_commanded
    new_dict['bb_temperature_measured_before'] = bb_temperature_measured_before
    new_dict['bb_temperature_measured_after'] = bb_temperature_measured_after
    new_dict['bb_voltage_measured_before'] = bb_voltage_measured_before
    new_dict['bb_voltage_measured_after'] = bb_voltage_measured_after
    new_dict['feedback_resistance'] = feedback_resistance
    new_dict['bias_resistance'] = bias_resistance
    new_dict['plot_data_in_ivmuxanalyze'] = True
    new_dict['multiplexedIV'] = multiplexedIV
    return new_dict

def coldloadControlInit():
    print('to be written')

def coldloadServoStabilizeWait(cc, temp, loop_channel,tolerance,postServoBBsettlingTime,tbbServoMaxTime):
    ''' servo coldload to temperature T and wait for temperature to stabilize '''
    if tbb>50.0:
        print('Blackbody temperature '+str(tbb)+ ' exceeds safe range.  Tbb < 50K')
        sys.exit()
    
    print('setting BB temperature to '+str(tbb)+'K')
    cc.setControlTemperature(temp=temp,loop_channel=loop_channel)
                
    # wait for thermometer on coldload to reach tbb --------------------------------------------
    is_stable = cc.isTemperatureStable(loop_channel,tolerance)
    stable_num=0
    while not is_stable:
        time.sleep(5)
        is_stable = cc.isTemperatureStable(loop_channel,tolerance)
        stable_num += 1
        if stable_num*5/60. > tbbServoMaxTime:
            break
             
    print('Letting the blackbody thermalize for ',postServoBBsettlingTime,' minutes.')
    time.sleep(60*postServoBBsettlingTime)
              
def iv_v_tbath(cfg,ec,adrTempControl,voltage_sweep_source,pickle_file,V_overbias,showPlot,verbose):
    ''' loop over bath temperatures and collect IV curves '''
    for jj, temp in enumerate(cfg['runconfig']['bathTemperatures']): # loop over temperatures
        if temp == 0: 
            print('temp = 0, which is a flag to take an IV curve as is without commanding the temperature controller.')
        elif cfg['voltage_bias']['overbias']: # overbias case
            overBias(adrTempControl=adrTempControl,voltage_sweep_source=voltage_sweep_source,
                     Thigh=cfg['voltage_bias']['overbiasThigh'],Tb=temp,Vbias=V_overbias,Tsensor=cfg['runconfig']['thermometerChannel'])
        else:
            adr.temperature_controller.SetTemperatureSetPoint(temp)
            stable = IsTemperatureStable(temp,adr=adrTempControl, Tsensor=cfg['runconfig']['thermometerChannel'],
                                         tol=cfg['runconfig']['temp_tolerance'],time_out=180.)
            if not stable:
                print('cannot obtain a stable temperature at %.3f mK !! I\'m going ahead and taking an IV anyway.'%(temp*1000))
                
        # Grab bath temperature before/after and run IV curve
        Tb_i = adrTempControl.GetTemperature(cfg['runconfig']['thermometerChannel'])
        v_arr, data_ret, flags = iv_sweep(ec=ec, vs=voltage_sweep_source, 
                                          v_start=cfg['voltage_bias']['v_start'], v_stop=cfg['voltage_bias']['v_stop'],v_step=cfg['voltage_bias']['v_step'],
                                          sweepUp=cfg['voltage_bias']['sweepUp'], showPlot=showPlot,verbose=verbose)
        Tb_f = adrTempControl.GetTemperature(cfg['runconfig']['thermometerChannel'])

        # save the data            
        if cfg['runconfig']['dataFormat']=='legacy':
            print('saving IV curve in legacy format')
            pd = {'temp':temp,'feedback_resistance':cfg['calnums']['rfb'], 'measured_temperature':Tb_f,
                  'bias_resistance':cfg['calnums']['rbias']}
            tes_pickle = tespickle.TESPickle(pickle_file)
            convertToLegacyFormat(v_arr,data_ret,nrows=ec.nrow,pd=pd,tes_pickle=tes_pickle,
                                  column=cfg['detectors']['Column'],mux_rows=cfg['detectors']['Rows'],column_index=0)
        else:
            print('Saving data in new format')
            # ret_dict keys: 'v', 'config', 'ivdict'
            # ivdict has structure: ivdict[iv##]: 'Treq', 'Tb_i', 'Tb_f','data','flags' 
            iv_dict['iv%02d'%jj]={'Treq':temp, 'Tb_i':Tb_i, 'Tb_f':Tb_f, 'data':data_ret, 'flags':flags}
            ret_dict = {'v':v_arr,'config':cfg,'ivdict':ivdict}
            pickle.dump( ret_dict, open( pickle_file, "wb" ) )

############################################################################################################
############################################################################################################
############################################################################################################
# main script starts here.

def main():

    # error handling
    # check if adr_gui running, dastard commander, cringe?, dcom ...

    verbose=False 
    showPlot=False

    # open config file
    with open(sys.argv[1], 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    # open tower config file
    with open(cfg['runconfig']['tower_config'], 'r') as ymlfile:
        tcfg = yaml.load(ymlfile)

    # determine column and rows
    baystring = 'Column' + cfg['detectors']['Column']
    if cfg['detectors']['Rows'] == 'all':
        mux_rows = list(range(32)) 
    else:
        mux_rows = list(cfg['detectors']['Rows'])

    # define where the data is store
    if not os.path.exists(cfg['io']['RootPath']):
        print('The path: %s does not exist! Making directory now.'%cfg['io']['RootPath'])
        os.makedirs(cfg['io']['RootPath'])
    localtime=time.localtime()
    thedate=str(localtime[0])+'%02i'%localtime[1]+'%02i'%localtime[2]
    filename = cfg['io']['RootPath']+cfg['detectors']['DetectorName']+'_'+baystring+'_ivs_'+thedate+'_'+cfg['io']['suffix']
    pickle_file=filename+'.pkl' 

    # defined tower card addresses for needed voltage sources
    bias_channel=tcfg['db_tower_channel_%s'%cfg['detectors']['Column']]
    sq2fb_tower_channel=tcfg['sq2fb_tower_channel_%s'%cfg['detectors']['Column']]

    # punt if you are asking for a temperature higher than 2K
    for t in cfg['runconfig']['bathTemperatures']:
        if t>2.0:
            print('setpoint temperature ',t,' greater than 2.0K.  Not allowed!  Abort!')
            sys.exit()
    
    # handle overbias voltage value; only used if overbias selected.
    if cfg['voltage_bias']['v_overbias']==None:
        V_overbias = cfg['voltage_bias']['v_start']
    else:
        V_overbias = cfg['voltage_bias']['v_overbias']

    print('\n\nStarting IV acquisition script on ',baystring,'*'*80,'\nRows: ',mux_rows,'\nTemperatures:',cfg['runconfig']['bathTemperatures'],'\nData will be saved in file: ',pickle_file)
    
    # instanciate needed classes ------------------------------------------------------------------------------------------------------------
    ec = EasyClient() # easy client for streaming data
    #c.setupAndChooseChannels() already done when initializing the class
    adr = AdrSystem(app=None, lsync=ec.lsync, number_mux_rows=ec.nrow, dfb_number_of_samples=ec.nSamp, doinit=False)
    voltage_sweep_source = BlueBox(port='vbox', version=cfg['voltage_bias']['source'], address=tcfg['db_tower_address'], channel=bias_channel)
    sq2fb = BlueBox(port='vbox', version='tower', address=tcfg['sq2fb_tower_address'], channel= sq2fb_tower_channel)
    #tes_pickle = tespickle.TESPickle(pickle_file)
    if 'coldload' in cfg.keys():
        if cfg['coldload']['execute']:
            cc = Cryocon22()
            cc.controlLoopSetup(loop_channel=cfg['coldload']['loop_channel'],control_temp=cfg['coldload']['bbTemperatures'][0],
                                t_channel=cfg['coldload']['t_channel'],PID=cfg['coldload']['PID'], heater_range=cfg['coldload']['heater_range']) # setup BB control

    if cfg['voltage_bias']['source']=='tower' and cfg['voltage_bias']['v_autobias']>2.5:
        print('tower can only source 2.5V.  Switching v_autobias to 2.5V')
        cfg['runconfig']['v_autobias']=2.5

    if cfg['runconfig']['setupTemperatureServo'] and cfg['runconfig']['bathTemperatures'][0] !=0: # initialize temperature servo if asked
        if adr.temperature_controller.getControlMode() == 'closed':
            t_set = adr.temperature_controller.getTemperatureSetPoint()
        else:
            t_set = 0.05
        setupTemperatureController(adrTempControl=adr.temperature_controller, channel=cfg['runconfig']['thermometerChannel'], \
                                   t_set=t_set,heaterRange=cfg['runconfig']['thermometerHeaterRange'],heaterResistance=100.0)
       
    # -----------------------------------------------------------------------------------------------------
    #Main loop starts here: loop over BB temperatures and bath temperatures, run multiplexed IVs 
    N = len(cfg['runconfig']['bathTemperatures'])
    iv_dict={} 

    if 'coldload' in cfg.keys(): 
        if cfg['coldload']['execute']:
            for ii, tbb in enumerate(cfg['coldload']['bbTemperatures']): # loop over coadload temps
                if tbb>50.0:
                    print('Blackbody temperature '+str(tbb)+ ' exceeds safe range.  Tbb < 50K')
                    sys.exit()
                elif tbb==0:
                    print('Tbb = 0 is a flag to take a current temperature.  No servoing')
                else:
                    cc.setControlState(state='on') # this command not needed every loop.  Too stupid to figure this out now.
                    if ii==0 and cfg['coldload']['immediateFirstMeasurement']: #skip the wait time for 1st measurement
                        postServoBBsettlingTime = 0
                    else: postServoBBsettlingTime = cfg['coldload']['postServoBBsettlingTime']
                        
                coldloadServoStabilizeWait(cc=cc, temp=tbb, loop_channel=cfg['coldload']['loop_channel'],
                                           tolerance=cfg['coldload']['temp_tolerance'], 
                                           postServoBBsettlingTime=postServoBBsettlingTime,
                                           tbbServoMaxTime=cfg['coldload']['tbbServoMaxTime'])

                iv_v_tbath(cfg,ec,adr.temperature_controller,voltage_sweep_source,pickle_file,V_overbias,showPlot,verbose)
        else:
            iv_v_tbath(cfg,ec,adr.temperature_controller,voltage_sweep_source,pickle_file,V_overbias,showPlot,verbose)
    else:
        iv_v_tbath(cfg,ec,adr.temperature_controller,voltage_sweep_source,pickle_file,V_overbias,showPlot,verbose)

    if cfg['voltage_bias']['setVtoZeroPostIV']:
        voltage_sweep_source.setvolt(0)     

if __name__ == '__main__': 
    main()
