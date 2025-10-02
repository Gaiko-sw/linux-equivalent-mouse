#!/usr/bin/python

## From github user yinonburgansky at https://gist.github.com/yinonburgansky/7be4d0489a0df8c06a923240b8eb0191

# calculation are based on http://www.esreality.com/index.php?a=post&id=1945096
# assuming windows 10 uses the same calculation as windows 7.
# guesses have been made calculation is not accurate
# touchpad users make sure your touchpad is calibrated with `sudo libinput measure touchpad-size`


import matplotlib.pyplot as pyplot
import struct
import argparse
import subprocess

def compare_samples(sample_points_x, sample_points_y):
    pyplot.plot(sample_points_x, sample_points_y, label=f'windows {args.sample_point_count} points')
    pyplot.plot(*sample_points(1024), label=f'windows 1024 points')
    pyplot.xlabel('device-speed')
    pyplot.ylabel('pointer-speed')
    pyplot.legend(loc='best')
    pyplot.show()

def main():
    print()
    parser = argparse.ArgumentParser(
        prog="Windows Accel Calculator",
    )

    # parser.exit_on_error = False
    
    # set according to your device:
    parser.add_argument("--xinput-device-id", required=True)
    parser.add_argument("--device-dpi", default=1000)
    parser.add_argument("--screen-dpi", default=157)
    parser.add_argument("--screen-scaling-factor", default=1)
    parser.add_argument("--sample-point-count", default=21) # should be enough but you can try to increase for accuracy of windows function
    parser.add_argument("--output-format", choices=["xinput", "libinput"], default="xinput")
    parser.add_argument("--execute-xinput", action='store_true', help="Actually run the xinput commands. Highly recommend running without first to verify the commands")

    sensitivity_group = parser.add_mutually_exclusive_group()
    sensitivity_group.add_argument("--sensitivity-factor", default=1.0)
    sensitivity_group.add_argument("--windows-sensitivity-notch", default=6)

    # sensitivity factor translation table: (windows slider notches)
    sensitivity_table = [
        0,
        0.1,
        0.2,
        0.4,
        0.6,
        0.8,
        1.0,
        1.2,
        1.4,
        1.6,
        1.8,
        2.0,
    ]

    args = parser.parse_args()
    # try:
    #     args = parser.parse_args()
    # except argparse.ArgumentError as e:
    #     if e.argument_name == "xinput_device_id":
    #         print(f"The following arguments are required: \"--xinput_device_id\"")
    #         print("Current devices according to `xinput`:")
    #         print(subprocess.check_output(['xinput', 'list']), text=True)

    if args.windows_sensitivity_notch:
        args.sensitivity_factor = sensitivity_table[args.windows_sensitivity_notch]

    # TODO: find accurate formulas for scale x and scale y
    # these are x and y as in the axes of the graph, where x is the physical speed and y is
    # the screen pointer speed

    # mouse speed: inch/s to device-units/millisecond
    scale_x = args.device_dpi / 1e3
    # pointer speed: inch/s to screen pixels/millisecond
    scale_y =  args.screen_dpi / 1e3 / args.screen_scaling_factor * args.sensitivity_factor

    # print(f'scale_x={scale_x}, scale_y={scale_y}')
    # print()

    def float16x16(num):
        return struct.unpack('<i', num[:-4])[0] / int(0xffff)

    # windows 10 registry values:
    # HKEY_CURRENT_USER\Control Panel\Mouse\SmoothMouseXCurve
    X = [
    b'\x00\x00\x00\x00\x00\x00\x00\x00',
    b'\x15\x6e\x00\x00\x00\x00\x00\x00',
    b'\x00\x40\x01\x00\x00\x00\x00\x00',
    b'\x29\xdc\x03\x00\x00\x00\x00\x00',
    b'\x00\x00\x28\x00\x00\x00\x00\x00',
    ]
    # HKEY_CURRENT_USER\Control Panel\Mouse\SmoothMouseYCurve
    Y=[
    b'\x00\x00\x00\x00\x00\x00\x00\x00',
    b'\xfd\x11\x01\x00\x00\x00\x00\x00',
    b'\x00\x24\x04\x00\x00\x00\x00\x00',
    b'\x00\xfc\x12\x00\x00\x00\x00\x00',
    b'\x00\xc0\xbb\x01\x00\x00\x00\x00',
    ]

    windows_points = [[float16x16(x), float16x16(y)] for x,y in zip(X,Y)]

    # print('Windows original points:')
    # for point in windows_points:
    #     print(point)
    # print()

    # # scale windows points according to device config
    points = [[x * scale_x, y * scale_y] for x, y in windows_points]

    # print('Windows scaled points')
    # for point in points:
    #     print(point)
    # print()


    # pyplot.plot(*list(zip(*windows_points)), label=f'windows points')
    # pyplot.plot(*list(zip(*points)), label=f'scaled points')
    # pyplot.xlabel('device-speed')
    # pyplot.ylabel('pointer-speed')
    # pyplot.legend(loc='best')
    # pyplot.show()


    def find2points(x):
        i = 0
        while i < len(points) - 2 and x >= points[i+1][0]:
            i +=1
        assert -1e6 + points[i][0] <= x <= points[i+1][0]+1e6, f'{points[i][0]} <= {x} <= {points[i+1][0]}'
        return points[i], points[i+1]


    def interpolate(x):
        (x0, y0), (x1, y1) = find2points(x)
        y = ((x-x0)*y1+(x1-x)*y0)/(x1-x0)
        return y


    def sample_points(count):
        # use linear extrapolation for last point to get better accuracy for lower points
        last_point = -2
        max_x = points[last_point][0]
        step = max_x / (count + last_point) # we need another point for 0
        sample_points_x = [si * step for si in range(count)]
        sample_points_y = [interpolate(x) for x in sample_points_x]
        return sample_points_x, sample_points_y


    sample_points_x, sample_points_y = sample_points(args.sample_point_count)
    step = sample_points_x[1] - sample_points_x[0]


    sample_points_str = ";".join(["%.3f" % number for number in sample_points_y])

    if args.output_format == 'libinput':
        print("== LibInput Parameters ==")
        print()
        print(f"libinput custom-step: {step}")
        print(f"libinput custom-points ({args.sample_point_count}):")
        print("\t", sample_points_str)

        print()
        print("libinput test:")
        print("\t", f"sudo ./builddir/libinput-debug-gui --verbose --set-profile=custom --set-custom-points=\"{sample_points_str}\" --set-custom-step={step:0.10f} --set-custom-type=motion")

        print('\nxinput libinput.conf Options:')
        print('\tOption "AccelProfile" "custom"')
        print(f'\tOption "AccelPointsMotion" "{sample_points_str.replace(";", " ")}"')
        print(f'\tOption "AccelStepMotion" "{step:0.10f}"')

    if args.output_format == 'xinput':
        print('== XInput set-props commands:')
        print()
        print(f'xinput set-prop {args.xinput_device_id} "libinput Accel Profile Enabled" 0, 0, 1')
        print(f'xinput set-prop {args.xinput_device_id} "libinput Accel Custom Motion Points" {sample_points_str.replace(";", ", ")}')
        print(f'xinput set-prop {args.xinput_device_id} "libinput Accel Custom Motion Step" {step:0.10f}')

    if args.execute_xinput:
        print('== Executing XInput Commands... ==')
        subprocess.call(f'xinput set-prop {args.xinput_device_id} "libinput Accel Profile Enabled" 0, 0, 1', shell=True)
        subprocess.call(f'xinput set-prop {args.xinput_device_id} "libinput Accel Custom Motion Points" {sample_points_str.replace(";", ", ")}', shell=True)
        subprocess.call(f'xinput set-prop {args.xinput_device_id} "libinput Accel Custom Motion Step" {step:0.10f}', shell=True)

if __name__ == "__main__":    
    main()