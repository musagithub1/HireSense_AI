"""
HireSense AI - Emotion Detection Model Tester
================================================
Pure NumPy inference — NO TensorFlow, NO Keras, NO JAX needed.
Loads weights directly from the TensorFlow.js binary shard files.
"""
import os
import json
import cv2
import numpy as np

# ── Layer implementations (pure NumPy) ──────────────────────────────

def conv2d(x, kernel, bias, padding='same'):
    """Conv2D with 'same' padding using im2col for speed.
    x: (H,W,C_in), kernel: (kH,kW,C_in,C_out)"""
    kh, kw, c_in, c_out = kernel.shape
    h, w = x.shape[0], x.shape[1]
    
    if padding == 'same':
        ph, pw = kh // 2, kw // 2
        x = np.pad(x, ((ph, ph), (pw, pw), (0, 0)), mode='constant')
    
    h_pad, w_pad = x.shape[0], x.shape[1]
    out_h, out_w = h_pad - kh + 1, w_pad - kw + 1
    
    # im2col approach for speed
    cols = np.zeros((out_h * out_w, kh * kw * c_in), dtype=np.float32)
    idx = 0
    for i in range(out_h):
        for j in range(out_w):
            cols[idx] = x[i:i+kh, j:j+kw, :].flatten()
            idx += 1
    
    kernel_flat = kernel.reshape(-1, c_out)  # (kh*kw*c_in, c_out)
    output = cols @ kernel_flat + bias       # (out_h*out_w, c_out)
    return output.reshape(out_h, out_w, c_out)

def batch_norm(x, gamma, beta, moving_mean, moving_var, epsilon=0.001):
    """Batch normalization (inference mode)."""
    return gamma * (x - moving_mean) / np.sqrt(moving_var + epsilon) + beta

def max_pool2d(x, pool_size=2, stride=2):
    """Max pooling 2D. x: (H,W,C)"""
    h, w, c = x.shape
    out_h, out_w = h // stride, w // stride
    # Reshape trick for fast pooling
    x_trimmed = x[:out_h*stride, :out_w*stride, :]
    return x_trimmed.reshape(out_h, stride, out_w, stride, c).max(axis=(1, 3))

def relu(x):
    return np.maximum(0, x)

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

def dense(x, kernel, bias):
    return x @ kernel + bias

# ── Weight loader ───────────────────────────────────────────────────

def load_tfjs_weights(model_dir):
    """Load weights from TensorFlow.js model.json and binary shards."""
    model_json_path = os.path.join(model_dir, 'model.json')
    with open(model_json_path, 'r') as f:
        model_config = json.load(f)
    
    manifest = model_config['weightsManifest'][0]
    
    all_bytes = b''
    for shard_path in manifest['paths']:
        full_path = os.path.join(model_dir, shard_path)
        with open(full_path, 'rb') as f:
            all_bytes += f.read()
    
    weights = {}
    offset = 0
    for w in manifest['weights']:
        shape = w['shape']
        num_elements = int(np.prod(shape)) if len(shape) > 0 else 1
        num_bytes = num_elements * 4
        data = np.frombuffer(all_bytes[offset:offset+num_bytes], dtype=np.float32)
        if len(shape) > 0:
            data = data.reshape(shape)
        weights[w['name']] = data.copy()
        offset += num_bytes
    
    return weights

# ── Forward pass ────────────────────────────────────────────────────

def predict(image, weights):
    """Run the full CNN forward pass. image: (48,48,1) float32 normalized.
    
    Architecture (from model.json):
      Conv2D(32, relu) -> BatchNorm -> MaxPool
      Conv2D(64, relu) -> BatchNorm -> MaxPool
      Conv2D(128, relu) -> BatchNorm -> MaxPool
      Flatten -> Dense(256, relu) -> Dropout -> Dense(128, relu) -> Dropout -> Dense(1, sigmoid)
    """
    x = image
    
    # Block 1: Conv2D(32, relu) -> BatchNorm -> MaxPool
    x = conv2d(x, weights['conv2d/kernel'], weights['conv2d/bias'])
    x = relu(x)  # relu is part of Conv2D activation
    x = batch_norm(x, weights['batch_normalization/gamma'], weights['batch_normalization/beta'],
                   weights['batch_normalization/moving_mean'], weights['batch_normalization/moving_variance'])
    x = max_pool2d(x)  # 48x48 -> 24x24
    
    # Block 2: Conv2D(64, relu) -> BatchNorm -> MaxPool
    x = conv2d(x, weights['conv2d_1/kernel'], weights['conv2d_1/bias'])
    x = relu(x)
    x = batch_norm(x, weights['batch_normalization_1/gamma'], weights['batch_normalization_1/beta'],
                   weights['batch_normalization_1/moving_mean'], weights['batch_normalization_1/moving_variance'])
    x = max_pool2d(x)  # 24x24 -> 12x12
    
    # Block 3: Conv2D(128, relu) -> BatchNorm -> MaxPool
    x = conv2d(x, weights['conv2d_2/kernel'], weights['conv2d_2/bias'])
    x = relu(x)
    x = batch_norm(x, weights['batch_normalization_2/gamma'], weights['batch_normalization_2/beta'],
                   weights['batch_normalization_2/moving_mean'], weights['batch_normalization_2/moving_variance'])
    x = max_pool2d(x)  # 12x12 -> 6x6
    
    # Flatten: 6x6x128 = 4608
    x = x.flatten()
    
    # Dense layers (dropout is off during inference)
    x = relu(dense(x, weights['dense/kernel'], weights['dense/bias']))
    x = relu(dense(x, weights['dense_1/kernel'], weights['dense_1/bias']))
    x = sigmoid(dense(x, weights['output/kernel'], weights['output/bias']))
    
    return float(x[0])

# ── Main ────────────────────────────────────────────────────────────

def main():
    tfjs_dir = os.path.join(os.path.dirname(__file__), '..', 'tfjs_model')
    
    if not os.path.exists(os.path.join(tfjs_dir, 'model.json')):
        print(f"❌ Error: Could not find model.json in {tfjs_dir}")
        return

    print("📦 Loading model weights from TensorFlow.js files...")
    weights = load_tfjs_weights(tfjs_dir)
    print(f"✅ Loaded {len(weights)} weight tensors!")

    # Quick sanity check with a test image
    print("\n🧪 Running sanity check...")
    test_black = np.zeros((48, 48, 1), dtype=np.float32)
    test_white = np.ones((48, 48, 1), dtype=np.float32)
    test_random = np.random.rand(48, 48, 1).astype(np.float32)
    score_black = predict(test_black, weights)
    score_white = predict(test_white, weights)
    score_random = predict(test_random, weights)
    print(f"   Black image  → score: {score_black:.4f}")
    print(f"   White image  → score: {score_white:.4f}")
    print(f"   Random image → score: {score_random:.4f}")

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    print("\n📷 Starting webcam... Press 'q' to quit.")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Could not open webcam.")
        return

    score = 0.5
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            resized = cv2.resize(face_roi, (48, 48)).astype(np.float32) / 255.0
            input_img = resized.reshape(48, 48, 1)

            frame_count += 1
            if frame_count % 5 == 0:
                score = predict(input_img, weights)
                print(f"   Raw score: {score:.6f}", end='\r')

            # Display with raw score for debugging
            label = "Stressed" if score > 0.5 else "Confident"
            color = (0, 0, 255) if score > 0.5 else (0, 255, 0)
            text = f"{label} (raw: {score:.3f})"

            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # Confidence bar (full range 0-1)
            bar_w = int(w * score)
            cv2.rectangle(frame, (x, y+h+5), (x+w, y+h+15), (50, 50, 50), -1)
            cv2.rectangle(frame, (x, y+h+5), (x+bar_w, y+h+15), color, -1)
            cv2.putText(frame, "Confident", (x, y+h+28), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,255,0), 1)
            cv2.putText(frame, "Stressed", (x+w-70, y+h+28), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,0,255), 1)

        cv2.putText(frame, "HireSense AI - Emotion Detector", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, "Press 'q' to quit", (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow('HireSense AI - Emotion Detection Tester', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n\n👋 Session ended!")

if __name__ == "__main__":
    main()
