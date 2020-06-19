#!/bin/bash
# Very slow implementation of hsl2rgb conversion

function comp() {
    if [[ "$(echo "$*" | bc -l)" -eq 0 ]]; then
        return 1;
    else
        return 0;
    fi;
}

function calc() {
    echo "$*" | bc -l;
}

function hue_to_rgb() {
    p=$1;
    q=$2;
    t=$3;
    if comp "$t < 0"; then
        t=`calc $t + 1`;
    fi;
    if comp "$t > 1"; then
        t=`calc $t - 1`;
    fi;
    if comp "$t < (1/6)"; then calc "$p + ($q - $p) * 6 * $t";
    elif comp "$t < (1/2)"; then calc "$q";
    elif comp "$t < (2/3)"; then calc "$p + ($q - $p) * (2/3 - $t) * 6";
    else echo $p; fi
}

function hsl_to_rgb() {
    hue=`calc $1 / 360`;  # 0..360
    sat=`calc $2 / 100`;  # 0..100
    bri=`calc $3 / 100`;  # 0..100
    red=0;
    grn=0;
    blu=0;
    if comp "$sat == 0"; then
        red=$bri;
        grn=$bri;
        blu=$bri;
    else
        if comp "$bri < 0.5"; then
            q=`calc "$bri * (1 + $sat)"`;
        else
            q=`calc "$bri + $sat - $bri * $sat"`;
        fi;
        p=`calc "2 * $bri - $q"`;
        red=`hue_to_rgb $p $q $(calc "$hue + (1 / 3)")`
        grn=`hue_to_rgb $p $q $hue`
        blu=`hue_to_rgb $p $q $(calc "$hue - (1 / 3)")`
    fi;
    echo "$red $grn $blu"
}
# hsl_to_rgb 90 100 75

# cat <<EOF >/dev/null
XOUT=`xrandr | grep primary | awk '{print$1}'`;

onexit() {
    xrandr --output $XOUT --gamma 1:1:1;
}
trap onexit EXIT;

while sleep 0.01; do
    unset red grn blu;
    hue=`echo "($(date +%s.%N) * 10) % 360" | bc`;
    gamma=`hsl_to_rgb $hue 90 75 | awk '{print $1":"$2":"$3}'`
    xrandr --output $XOUT --gamma $gamma;
    echo $gamma;
done
# EOF
