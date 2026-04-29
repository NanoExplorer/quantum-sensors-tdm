# CRINGE: CRate Interface for Next Generation Electronics

CRINGE is the control interface for the Crate, the NIST Time Domain Multiplexer (TDM) room-temperature readout electronics. It provides graphical controls to set all parameters of the TDM system, as well as socket support for controlling the system from scripts (see cringe_control.py), and an embedded IPython terminal for more in-depth scripts. (Depending on your needs, you'll have to choose between making an embeddable ipython script or a standalone script using socket-based commands.)

CRINGE also includes support for controlling the Tower (more warm electronics which provide biasing and preamplification and is attached to the cryostat).

## Controlling Cringe via socket
This is how most of the scripts in the broader Quantum Sensors TDM repository interact with CRINGE. The adr_gui uses it to power off the crate before running a magnet cycle, and most of the scripts in detchar/ use it to command biases to the tower. 


## Controlling Cringe via IPython
This is a relatively new and dare I say more kludgey method. In the squidchar folder is the squid_mux_cringe_plugin.py which is designed to be imported into the CRINGE IPython with a magic command (`%run -i squid_mux...` I think.)

## CRINGE Features in this branch:
**Breaking change**: This branch of CRINGE does not support SCREAM cards (Single Channel REAdout Module I think). If anyone is using these I'd be curious to know.

This branch of CRINGE is based on the one in Velma (see below). The major change is that an asynchronous worker has been implemented (mostly by AI, then tested and reviewed) to run in a separate thread and handle communication with DFB cards. This eliminates the issue where you could lock up CRINGE for a minute or two by clicking on the DAC A or B offset spinbox and then holding down an arrow key to change its value. It probably introduces edge cases though, which is why it is quarantined on its own branch for now.

A more minor change is that the "tower power gui" is now integrated into the tower tab. Instead of launching a new window you can now power the tower directly. On systems without `namedserialrc` entries for the tower, these new buttons *should* remain greyed-out and disabled, but this has not been tested. 

Internally, tons of code has been removed. Most of it has been shifted into `.ui` files which are editable in WYSIWYG QT-Designer (make sure to get QT-5 designer though, because otherwise it will mangle the ui files so that QT-6 can read them). The main motivation for this is to make it easier to find the relevant logic. At last count, this branch of CRINGE has 9,000 lines of code as compared with the main branch which has 14,000. I'm glad I'm not being paid per line...


Velma branch CRINGE is standard except that IPython allows access to the main window and QT application by exporting the variables, and it will prompt you to save a file if you close the application. 

This branch also sets the step size for the tower spinboxes to 25 DAC units, instead of the default 250.
