tomo_preprocess documentation:

Author: Robert Stass
Email: robertstass@strubi.ox.ac.uk
Address: OPIC, Strubi, University of Oxford



Dependencies:
* MotionCor2 (version motioncor2_10192016 or later for dose weighting)
* Bsoft - Must be in $PATH
- mrcfile python library by Colin Palmer at CCP-EM. A version of this (mrcfile 1.0.0) is included in the repository for convenience.
        Thanks to Colin and CCP-EM for this very useful tool! download: https://pypi.python.org/pypi/mrcfile
- pyrelion python library. A version is included in the repository for convenience. Also available here https://github.com/OPIC-Oxford/pyrelion-scripts.
- numpy python library (for custom dose weighting)
- python 2.7



About:
tomo_preprocess performs four common preprocessing functions for tomographic tilt series data before further processing (eg with etomo)
    -Motion correction with motioncor2
    -Sorting the images into the correct order (especially needed for more complicated tilt schemes)
    -Applying dose weighting to the images according to the Grant & Grigorieff (2015) paper.
    -Ctf estimation with relion_run_ctffind. This produces a star file that can later be converted to an imod .defocus file.

For most data sets this can be done with a single command.

In theory motioncor2 should be capable of applying the dose weighting itself but the -InitDose parameter doesn't currently
work as expected. Therefore a separate script 'tomo_dose_filter' is included. This can be ran using the --do_custom_doseweighting
 or separately on existing stacks.







Usage:
First source the script using the .cshrc or .bashrc scripts provided.
A typical example of how to use this script:

if you have multiple tilt series in folders named 01 02 03 ect... each containing files named according to the pattern ?????_??.??.??.mrc

    tomo_motioncor2 --input_folders "??" -i "?????_??.??.??.mrc" --tilt_scheme  continuous_positive --min_angle -30 --angle_step 3 -apix 1.35 --dose_per_movie 4.0 --do_custom_doseweighting

(another useful argument initially is --only_make_batch_file that will create a batch file that can be checked and edited before actually running it)

(NB tomo_preprocess and tomo_motioncor2 are the same thing under the hood)
Alternatively it can be ran on a single tilt series without the --input_folders option





Outputs:

tomo_motioncor2 / tomo_preprocess will output a motion corrected stack <tomo_name>.st
if --do_custom_doseweighting is set a <tomo_name>_dw.st stack will also be produced.
if --do_motioncor2_doseweighting is set a <tomo_name>_DW.st stack will also be produced. Not recommended.



Tilt schemes:
The following tilt schemes are currently supported:

    --continuous_positive: Starting from the most negative tilt angle and collecting the rest in a continuous sweep in a
                            positive direction.
                            e.g.  1,2,3,4,5,6,7,8,9

    --continuous_negative: Starting from the most positive tilt angle and collecting the rest in a continuous sweep in a
                            negative direction
                            e.g.  9,8,7,6,5,4,3,2,1

    --bidirectional_positive: Starting from the angle specified by --starting_angle and initially stepping in a positive
                                direction to the most positive tilt angle. Then returning to the start angle minus 1 step
                                and collecting the rest in a negative direction.
                                e.g.    9,8,7,6,1,2,3,4,5
                                e.g.    9,8,1,2,3,4,5,6,7

    --bidirectional_negative: Starting from the angle specified by --starting_angle and initially stepping in a negative
                                direction to the most negative tilt angle. Then returning to the start angle plus 1 step
                                and collecting the rest in a positive direction.
                                e.g.    5,4,3,2,1,6,7,8,9
                                e.g.    7,6,5,4,3,2,1,8,9

    --dose_symmetric_positive: Starting from the angle specified by --starting_angle (usually zero) and taking the first
                                step in a positive direction. Then switching to the same angle in the negative direction
                                and continue the rest of the tilt series in this symmetric manner. (if the starting angle
                                is offset from centre the rest of the tilt series will be filled in continuously away from
                                the centre).
                                e.g.    9,7,5,3,1,2,4,6,8
                                e.g.    9,8,7,6,5,3,1,2,4 (offset starting angle)

    --dose_symmetric_negative: Starting from the angle specified by --starting_angle (usually zero) and taking the first
                                step in a negative direction. Then switching to the same angle in the positive direction
                                and continue the rest of the tilt series in this symmetric manner. (if the starting angle
                                is offset from centre the rest of the tilt series will be filled in continuously away from
                                the centre).
                                e.g.    8,6,4,2,1,3,5,7,9
                                e.g.    6,4,2,1,3,5,7,8,9 (offset starting angle)




For unsupported tilt schemes or times where some files are missing there are some other options to input your own tilt information.

    - there is a --custom_tilt_order parameter which is consecutive list of integers showing the order the tilt series was taken in.
        This is applied to every tilt series given.
    - a tilt.order file can be placed in the same directory as the tilt images. This is used if the --use_tilt_order_files
        parameter is included. (if a file can't be found the standard tilt info parameters are used) This file is a
        consecutive list of integers showing the order the tilt series was taken in with the following format:

        9
        8
        7
        6
        1
        2
        3
        4
        5

        A second column can (optionally) be included with the accumulated dose received after the image is recorded. eg:

        9   19.1
        8   18.1
        7   17.1
        6   16.1
        1   10.1
        2   12.1
        3   13.1
        4   14.1
        5   15.1


Ctf estimation:
    This is done by the tomo_ctf_estimate script.
    This will do two things:
        -Sort the motion corrected micrographs into a micrograph star file in tilt order (-ve to +ve) based on the tilt scheme used.
        -Ctf estimation is done using 'relion_run_ctffind' which is wrapper that can use ctffind3, ctffind4 or gctf (relion 2 only)
        (alternatively you can just produce the sorted micrograph star file and use that for ctf estimation with the relion gui)
    This will output a star file with estimated ctf parameters in tilt order (and separated by tilt series)

    example usage: tomo_ctf_estimate --input_folders "tomo_???" -i "tomo_*_*_?????_??.??.??.mrc" -apix 2.0 --tilt_scheme bidirectional_negative --min_angle -30 --angle_step 3 --rln_version 2 --ctf_software ctffind4 --ctf_exe /apps/strubi/ctf/4.1.5/ctffind --ResMin 50 --ResMax 7
    The same options can be passed to the main tomo_preprocess script with the additional argument --do_ctf_estimation


    Once your tilt series has been aligned you can write the data in the star file to imod .defocus files.
     (This needs to be done after tilt series alignment because the tilt angles and (for astigmatism) angular rotation between .ali and .st are needed.
    To do this use tomo_write_imod_defocus with these options:
        -i <wildcard to imod .edf project files>
        --ctf_star <the star file from tomo_ctf_estimate>
        --version The version of imod defocus file you want to write. (version 3 files include astigmatism but only work with later versions of imod (4.9+))

    (It's very important that the micrographs in the star file remain in tilt order and separated by tilt series)


tomo_doseweight_sharpen:

When applying dose weighting to the original images (with tomo_dose_filter), the low frequency information gets amplified
relative to the high frequency information. This results in maps that are unsharp (blurry). One method to (approximately)
correct for this is to b-factor sharpen the final maps but this is an imperfect correction and the appropriate b-factor
is difficult to estimate for maps at resolutions worse than 10A. Instead the tomo_doseweight_sharpen script can be used
to perfectly correct for the dose weighting induced blurring. In the single particle case, this correction is applied during
motion correction of image frames so it is equally appropriate to apply this correction to the tomogram/subvolumes prior
to refinement.