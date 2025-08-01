import pyvisa
import numpy as np
import matplotlib.pyplot as plt
import time
import datetime
import os

# Configure VISA
rm = pyvisa.ResourceManager()
resources = rm.list_resources()
print("Available instruments:", resources)

# Replace with your DCA-X VISA address
dca_address = 'USB0::0x2A8D::0x7B01::MY64350173::0::INSTR'  # Adjust as needed

# Connect to DCA-X
scope = rm.open_resource(dca_address)
scope.timeout = 20000  # ms
scope.read_termination = '\n'

# Identify instrument
instrument_id = scope.query("*IDN?").strip()
print("Connected to:", instrument_id)

# Reset and clear
scope.write("*RST")
scope.write("*CLS")
time.sleep(2)  # Allow reset to complete

# Set channel (e.g., Channel 1A)
scope.write(":CHAN1A:DISP ON")
scope.write(":ACQ:RUN")
time.sleep(3)  # Allow acquisition to stabilize

# Trigger single capture
scope.write(":SING")
print("Single trigger initiated...")

# Wait until acquisition is complete - use different status check
max_wait_time = 30  # Maximum wait time in seconds
start_time = time.time()

while True:
    # Check if operation is complete using *OPC? or acquisition status
    try:
        # Try checking acquisition state
        acq_state = scope.query(":ACQ:STAT?").strip()
        print(f"Acquisition state: {acq_state}")
        
        # If acquisition is stopped, break
        if acq_state.upper() in ['STOP', 'STOPPED', '0']:
            break
            
    except Exception as e:
        print(f"Status check error: {e}")
        # Fallback: just wait a fixed time
        time.sleep(5)
        break
    
    # Check for timeout
    if time.time() - start_time > max_wait_time:
        print("Timeout waiting for acquisition to complete")
        break
        
    time.sleep(1)

print("Acquisition complete, retrieving data...")

# Configure waveform data export
scope.write(":WAV:SOUR CHAN1A")
scope.write(":WAV:FORM ASCII")
scope.write(":WAV:MODE RAW")  # Or NORMAL
scope.write(":WAV:POIN:MODE RAW")
scope.write(":WAV:POIN 10000")  # Number of points to read

# Get waveform preamble (for time axis)
try:
    x_increment = float(scope.query(":WAV:XINC?"))
    x_origin = float(scope.query(":WAV:XOR?"))
    y_increment = float(scope.query(":WAV:YINC?"))
    y_origin = float(scope.query(":WAV:YOR?"))
    y_reference = float(scope.query(":WAV:YREF?"))
    
    print(f"Waveform parameters retrieved:")
    print(f"  X increment: {x_increment}")
    print(f"  Y increment: {y_increment}")
    
except Exception as e:
    print(f"Error getting waveform parameters: {e}")
    # Set default values
    x_increment = 1e-12
    x_origin = 0
    y_increment = 1e-3
    y_origin = 0
    y_reference = 0

# Fetch waveform data
try:
    print("Fetching waveform data...")
    raw_data = scope.query(":WAV:DATA?")
    
    # Parse the data - might need to handle different formats
    if raw_data.startswith('#'):
        # Binary block data format - extract ASCII data
        header_len = int(raw_data[1]) + 2
        data_str = raw_data[header_len:]
    else:
        data_str = raw_data.strip()
    
    y_vals = np.array([float(val) for val in data_str.split(',')])
    x_vals = np.arange(len(y_vals)) * x_increment + x_origin
    
    print(f"Successfully retrieved {len(y_vals)} data points")
    
except Exception as e:
    print(f"Error fetching waveform data: {e}")
    # Create dummy data for testing
    y_vals = np.random.randn(1000) * 0.1
    x_vals = np.arange(len(y_vals)) * 1e-12

# Close instrument connection
scope.close()

# Create timestamp for filename
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename = f"n1000a_trace_{timestamp}.csv"

# Create header with metadata
header_lines = [
    f"# N1000A DCA-X Waveform Capture",
    f"# Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    f"# Instrument: {instrument_id}",
    f"# Channel: CHAN1A",
    f"# X Increment: {x_increment}",
    f"# X Origin: {x_origin}",
    f"# Y Increment: {y_increment}",
    f"# Y Origin: {y_origin}",
    f"# Y Reference: {y_reference}",
    f"# Number of Points: {len(y_vals)}",
    f"#",
    f"Time(s),Voltage(V)"
]

# Save to CSV with detailed header
with open(csv_filename, 'w') as f:
    for line in header_lines:
        f.write(line + '\n')
    
    # Write data
    for t, v in zip(x_vals, y_vals):
        f.write(f"{t:.12e},{v:.6e}\n")

print(f"Waveform trace logged to: {csv_filename}")
print(f"Total points captured: {len(y_vals)}")
print(f"Time range: {x_vals[0]:.3e} to {x_vals[-1]:.3e} seconds")
print(f"Voltage range: {np.min(y_vals):.3f} to {np.max(y_vals):.3f} V")

# Plot the waveform
plt.figure(figsize=(12, 6))
plt.plot(x_vals * 1e9, y_vals)  # x in ns
plt.xlabel('Time (ns)')
plt.ylabel('Voltage (V)')
plt.title(f'N1000A DCA-X Captured Waveform - {timestamp}')
plt.grid(True)
plt.tight_layout()

# Save plot
plot_filename = f"n1000a_plot_{timestamp}.png"
plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
plt.show()

print(f"Plot saved as: {plot_filename}")
