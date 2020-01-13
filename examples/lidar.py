# Copyright (C) 2019 Analog Devices, Inc.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#     - Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     - Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#       the documentation and/or other materials provided with the
#       distribution.
#     - Neither the name of Analog Devices, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#     - The use of this software may or may not infringe the patent rights
#       of one or more patent holders.  This license does not release you
#       from the requirement that you obtain separate licenses from these
#       patent holders to use this software.
#     - Use of the software either in source or binary form, must be run
#       on or directly connected to an Analog Devices Inc. component.
#
# THIS SOFTWARE IS PROVIDED BY ANALOG DEVICES "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, NON-INFRINGEMENT, MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED.
#
# IN NO EVENT SHALL ANALOG DEVICES BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, INTELLECTUAL PROPERTY
# RIGHTS, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
# THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


# This example creates a GUI for configuring, controlling and capturing samples
# from a Lidar board. You can select the pulse width, trigger level, apd bias
# and tilt voltage, among others. The Start buttons starts the capturing of
# samples witch are displayed on the top of the GUI.

# The channel 0 (reference signal) and channel 1 (return signal) are enabled and
# used to determine the distance with a correlation method. The distance is
# displayed in the bottom half of the GUI. Because displaying the distance
# measurement in real time would mean updating the plot much to often to be
# useful to the eyes, a method is used to only display the average measured
# distance of the last 10 samples.

import iio
from adi.fmclidar1 import fmclidar1

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from scipy import signal

lidar = None                    # Lidar context
NSAMPLES = 10
# Keep count of distance measurements for each sample and for all channels.
# One channel is used for the reference signal.
all_channels_samples = [[] for i in range(16)]
distances = [[] for i in range(16)] 
meas_distance_mean = [0 for i in range (16)]
mean_samples_count = [NSAMPLES for i in range (16)]
mean_samples_sum   = [0 for i in range (16)]

def cont_capt():
    """Continuously request samples after Start is pressed."""
    if button_txt.get() == "Start":
        button_txt.set("Stop")
    else:
        button_txt.set("Start")
    while button_txt.get() == "Stop":
        single_capt()
        # sleep(TIMEOUT_SAMPLES)

def single_capt():
    """Display info about a single capture."""
    if 'sample_number' not in single_capt.__dict__:
        single_capt.sample_number = 0
    samples = lidar.rx()
    ref = samples[0] # Reference signal    
    ref = ref - np.mean(ref) # Adjust to zero
        
    for i, s in enumerate(samples, start=0):        
        if (len(s) == 0):
            continue
        global meas_distance_mean
        global mean_samples_count
        global mean_samples_sum
        
        corr_lidar = np.correlate(ref, s, mode='full')
        lag_lidar = corr_lidar.argmax() - (len(s) - 1)
        # Adjust for system offset
        lag_lidar -= 8
        meas_distance = abs(lag_lidar*15)           
        alpha = 1
        meas_distance_mean[i] = (meas_distance * alpha) + (meas_distance_mean[i] * (1-alpha))
        if mean_samples_count[i] > 0:
            mean_samples_sum[i] += meas_distance_mean[i]
            mean_samples_count[i] -= 1
        else:
            distance_plot.cla()
            distance_plot.grid(True)
            distance_plot.set_title('Distance Approximation')
            distance_plot.set_xlabel('Sample number')
            distance_plot.set_ylabel('Distance (cm)')
            distance_plot.bar(range(MAX_SAMPLES), [0] * MAX_SAMPLES)            
            dist = mean_samples_sum[i] / NSAMPLES
            distances[i].append(dist)
            for j, d in enumerate(distances, start=0):
                if len(d) == 0:
                    continue                
                distance_plot.plot(d, label=str(d[-1]))
            distance_plot.legend()
            mean_samples_sum[i] = 0
            mean_samples_count[i] = NSAMPLES
            # single_capt.sample_number += 1
            # if single_capt.sample_number > MAX_SAMPLES:
            #     distance_plot.set_xlim([single_capt.sample_number - MAX_SAMPLES,
            #                             single_capt.sample_number])

    # Plot data
    signal_plot.cla()
    signal_plot.set_title('Pulse Shape')
    signal_plot.set_xlabel('Time (ns)')
    signal_plot.set_ylabel('ADC Codes')
    signal_plot.set_ylim([-30, 130])
    signal_plot.grid(True)

    for i, s in enumerate(samples, start=0):
        if (len(s) == 0):
            continue
        signal_plot.plot(s, label="Channel" + str(i))
        
    try:
        a.plot(top_edge, x[top_edge], 'X')
        a.plot(bottom_edge, x[bottom_edge], 'X')
        a.axvline(x=TIME_OFFSET, color='green', label="Cal Offset")
        a.axvline(x=mid_point, color='red', label='Mid point')
    except:
        pass
    signal_plot.legend()
    canvas.draw()
    
    root.update_idletasks()
    root.update()

def config_board():
    global lidar
    global distances
    global meas_distance_mean
    global mean_samples_count
    global mean_samples_sum
    if lidar == None:
        try:
            lidar = fmclidar1(uri="ip:" + ip_addr.get())
            lidar.rx_buffer_size = 1024
            lidar.laser_enable()            
        except:
            txt1.insert(tk.END, 'No device found.\n')
            return    
    lidar.laser_pulse_width = int(pw.get())
    lidar.laser_frequency = int(pulse_freq.get())
    lidar.apdbias     = float(apd_voltage.get())
    lidar.tiltvoltage = float(tilt_voltage.get())    
    lidar.channel_sequencer_opmode = seq_mode.get()    
    lidar.channel_sequencer_order_manual_mode = manual_mode_order.get()

    # Clear the distance measurement and display
    distances          = [[] for i in range(16)] 
    meas_distance_mean = [0 for i in range (16)]
    mean_samples_count = [NSAMPLES for i in range (16)]
    mean_samples_sum   = [0 for i in range (16)]    

root = tk.Tk()
root.title("TOF Demo")

DEFAULT_IP           = '10.48.65.153'
DEFAULT_PULSE_WIDTH  = '20'
DEFAULT_FREQUENCY    = '1000'
DEFAULT_TRIG_LEVEL   = '-10'
DEFAULT_APD_VOLTAGE  = '-160.0'
DEFAULT_TILT_VOLTAGE = '1.0'

TIME_OFFSET     = 167.033333
RUN_DUMMY_DATA  = 0
MAX_SAMPLES     = 30                # Number of distance measurement samples shown in plot
TIMEOUT_SAMPLES = 0.5

# Config attributes
ip_addr = tk.StringVar()
ip_addr.set(DEFAULT_IP)

pw = tk.StringVar()
pw.set(DEFAULT_PULSE_WIDTH)

pulse_freq = tk.StringVar()
pulse_freq.set(DEFAULT_FREQUENCY)

trig_level = tk.StringVar()
trig_level.set(DEFAULT_TRIG_LEVEL)

apd_voltage = tk.StringVar()
apd_voltage.set(DEFAULT_APD_VOLTAGE)

tilt_voltage = tk.StringVar()
tilt_voltage.set(DEFAULT_TILT_VOLTAGE)

fr1 = tk.Frame(root)
fr1.pack(side = tk.LEFT, anchor = 'n', padx = 10)

fr2 = tk.Frame(fr1)
fr2.grid(row = 0, column = 0, pady = 10)

label1 = tk.Label(fr2, text = "IP Addressss: ")
label1.grid(row = 0, column = 0)

entry1 = tk.Entry(fr2, textvariable=ip_addr)
entry1.grid(row = 0, column = 1)

label2 = tk.Label(fr2, text = "Pulse Width (ns): ")
label2.grid(row = 1, column = 0)

entry2 = tk.Entry(fr2, textvariable=pw)
entry2.grid(row = 1, column = 1)

label3 = tk.Label(fr2, text = "Rep Rate (Hz): ")
label3.grid(row = 2, column = 0)

entry3 = tk.Entry(fr2, textvariable=pulse_freq)
entry3.grid(row = 2, column = 1)

label7 = tk.Label(fr2, text = "APD Bias (V): ")
label7.grid(row = 3, column = 0)

entry7 = tk.Entry(fr2, textvariable=apd_voltage)
entry7.grid(row = 3, column = 1)

label8 = tk.Label(fr2, text = "Tilt Voltage (V): ")
label8.grid(row = 4, column = 0)

entry8 = tk.Entry(fr2, textvariable=tilt_voltage)
entry8.grid(row = 4, column = 1)

seq_mode = tk.StringVar(root)
seq_mode.set("auto")
tk.OptionMenu(fr2, seq_mode, "manual", "auto").grid(row=6, column=0)

manual_mode_order = tk.StringVar(root)
manual_mode_order.set("0 0 0 0")
tk.Entry(fr2, textvariable=manual_mode_order).grid(row=6, column=1)

label5 = tk.Label(fr2, text = "", font=("Arial", 20, "bold"))
label5.grid(row = 8, column = 1)

button_txt = tk.StringVar()
button = tk.Button(fr2, textvariable=button_txt, command=cont_capt)
button_txt.set("Start")
button.config(width = 10, height = 1)
button.grid(row = 7, column = 1, pady = 10)

config_button = tk.Button(fr2, text="Config Board", command=config_board)
config_button.config(width = 10, height = 1)
config_button.grid(row = 7, column = 0, pady = 10)

fr3 = tk.Frame(fr1)
fr3.grid(row = 3, column = 0)

label2 = tk.Label(fr3, text = "Message Log: ")
label2.grid(row = 0, column = 0)

txt1 = tk.Text(fr3, width = 40, height = 2)
txt1.grid(row = 4, column = 0)

fig = plt.figure(figsize=(15,10))
signal_plot = fig.add_subplot(211)
signal_plot.set_title('Pulse Shape')
signal_plot.set_xlabel('Time (ns)')
signal_plot.set_ylabel('ADC Codes')

distance_plot = fig.add_subplot(212)

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(side = tk.LEFT, pady = 10, padx = 10, anchor = 'n')
canvas.draw()
root.update_idletasks()

config_board()
root.update()
