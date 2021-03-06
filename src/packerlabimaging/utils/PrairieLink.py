# PrairieLink
# Lloyd Russell 2017

import os
import numpy as np
import time
import tkinter as tk
from tkinter import filedialog


def ReadRawFile(movie_path=None, start=1, stop=np.Inf, num_frames=np.Inf, verbose=False):
	"""
	Input
	-----
	movie_path : string, optional
		full path to *.bin file, if none provided dialog box will open
	start : int, optional
		the first frame to begin reading from
	stop : int, optional
		the frame to stop reading at
	num_frames : int, optional
		the total number of frames to read
	verbose : bool, optional
		choose whether to display output progress and stats
	Output
	------
	cellsdata : np.ndarray
		frames x rows x cols array (dtype=np.uint16)
	"""

	# open file diaog if input not provided
	if not movie_path:
		root = tk.Tk()
		root.withdraw()
		movie_path = filedialog.askopenfilename(filetypes=(("BIN files", "*.bin*"), ("All files", "*.*") ))

	if verbose:
		print('File path: ' + movie_path)

	# begin timer
	time_started = time.time()

	# open file and read cellsdata
	with open(movie_path, 'rb') as f:
		# extract details from header
		pixels_per_line = int(np.fromfile(f, dtype=np.uint16, count=1)[0])
		lines_per_frame = int(np.fromfile(f, dtype=np.uint16, count=1)[0])
		samples_per_frame = pixels_per_line * lines_per_frame

		# Find number of frames in file
		filesize_bytes = os.path.getsize(movie_path)
		total_num_frames = int(((filesize_bytes/2) - 2) / samples_per_frame)  # divide by 2 because format is uint16  subtract 2 because file header

		if verbose:
			print('File size: ' + str(total_num_frames) + ' frames (' + str(pixels_per_line) + ', ' + str(lines_per_frame) + ')')

		# Define read limits
		if stop == np.Inf:
			stop = start + num_frames
		if stop > total_num_frames:
			num_frames = total_num_frames - (start-1)
			stop = total_num_frames
		else:
			num_frames = stop - start

		if verbose:
			print('Requested: ' + str(num_frames) + ' frames, from ' + str(start) + ' to ' + str(stop))

		# Read cellsdata
		start_on_byte = (((start-1) * samples_per_frame)+2) *2  # plus 2 because header size, x2 because 1 uint16 is 2 bytes
		num_chars_to_read = (num_frames * samples_per_frame)  # note size in bytes of char defined by fread function argument
		f.seek(start_on_byte, 0)
		data = np.fromfile(f, dtype=np.uint16, count=num_chars_to_read)

	# Reshape cellsdata into frame array
	data = data.reshape(num_frames, lines_per_frame, pixels_per_line, order='C')

	if verbose:
		print('Data size: ' + str(data.shape[0]) + ' frames (' + str(data.shape[1]) + ', ' + str(data.shape[2]) + ')')

	time_taken = time.time() - time_started
	if verbose:
		print('Time taken: ' + '{0:.2f}'.format(time_taken) + ' s')

	return data


def WriteRawFile(data, file_name):
	# construct filename
	if not file_name[-4:] == '.bin':
		file_name = file_name + '.bin'

	num_rows = np.uint16(data.shape[1])
	num_cols = np.uint16(data.shape[2])

	with open(file_name, 'wb') as raw_file:
		# write the header
		num_rows.tofile(raw_file)
		num_cols.tofile(raw_file)

		# write the cellsdata
		data.tofile(raw_file)