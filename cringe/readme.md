# CRINGE: CRate Interface for Next Generation Electronics

CRINGE is the control interface for the Crate, the NIST Time Domain Multiplexer (TDM) room-temperature readout electronics. It provides graphical controls to set all parameters of the TDM system, as well as socket support for controlling the system from scripts (see cringe_control.py), and an embedded IPython terminal for more in-depth scripts. (Depending on your needs, you'll have to choose between making an embeddable ipython script or a standalone script using socket-based commands.)

CRINGE also includes support for controlling the Tower (more warm electronics which provide biasing and preamplification and is attached to the cryostat).

## Controlling Cringe via socket
This is how most of the scripts in the broader Quantum Sensors TDM repository interact with CRINGE. The adr_gui uses it to power off the crate before running a magnet cycle, and most of the scripts in detchar/ use it to command biases to the tower. 


## Controlling Cringe via IPython
This is a relatively new and dare I say more kludgey method. In the squidchar folder is the squid_mux_cringe_plugin.py which is designed to be imported into the CRINGE IPython with a magic command (`%run -i squid_mux...` I think.)

## CRINGE Features in this branch:
This branch of CRINGE is standard except that IPython allows access to the main window and QT application by exporting the variables, and it will prompt you to save a file if you close the application. 

This branch also sets the step size for the tower spinboxes to 25 DAC units, instead of the default 250.
