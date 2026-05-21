#!/bin/bash
echo "Starting resilient download for OpenCV and TensorFlow..."
echo "This script uses wget -c to automatically resume if your connection drops!"

OPENCV_URL="https://files.pythonhosted.org/packages/fd/55/b3b49a1b97aabcfbbd6c7326df9cb0b6fa0c0aefa8e89d500939e04aa229/opencv_python-4.13.0.92-cp37-abi3-manylinux_2_28_x86_64.whl"
TF_URL="https://files.pythonhosted.org/packages/14/b4/3a79d023f03b2260ff0df56de0b0731fca02d6bce393ea9379854497cc3e/tensorflow-2.21.0-cp313-cp313-manylinux_2_27_x86_64.whl"

until wget -c $OPENCV_URL; do
    echo "Connection dropped. Resuming OpenCV download in 2 seconds..."
    sleep 2
done

until wget -c $TF_URL; do
    echo "Connection dropped. Resuming TensorFlow download in 2 seconds..."
    sleep 2
done

echo "Downloads complete! Installing local packages..."
source ~/Downloads/HireSense_AI_v6/venvv/bin/activate
pip install opencv_python-4.13.0.92-cp37-abi3-manylinux_2_28_x86_64.whl tensorflow-2.21.0-cp313-cp313-manylinux_2_27_x86_64.whl

echo "Installation finished successfully! You can now run the tester script."
