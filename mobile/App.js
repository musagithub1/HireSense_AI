import React, { useState, useRef } from 'react';
import { 
  StyleSheet, 
  SafeAreaView, 
  ActivityIndicator, 
  Image,
  View, 
  Text, 
  TouchableOpacity, 
  StatusBar 
} from 'react-native';
import { WebView } from 'react-native-webview';

const HIRESENSE_URL = (process.env.EXPO_PUBLIC_HIRESENSE_URL || "").trim();
const URL_IS_CONFIGURED = /^https:\/\/[^.\s][^\s]*$/i.test(HIRESENSE_URL);

export default function App() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const webViewRef = useRef(null);

  const handleReload = () => {
    setError(false);
    setLoading(true);
    if (webViewRef.current) {
      webViewRef.current.reload();
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#07101f" />
      
      {!URL_IS_CONFIGURED ? (
        <View style={styles.errorContainer}>
          <Image
            source={require("./assets/hiresense-ai-logo.png")}
            style={styles.logo}
            resizeMode="contain"
            accessibilityLabel="HireSense AI"
          />
          <Text style={styles.errorTitle}>Deployment URL required</Text>
          <Text style={styles.errorText}>
            Set EXPO_PUBLIC_HIRESENSE_URL to your HTTPS Streamlit deployment
            before starting the mobile wrapper.
          </Text>
        </View>
      ) : !error ? (
        <WebView 
          ref={webViewRef}
          source={{ uri: HIRESENSE_URL }}
          style={styles.webview}
          onLoadStart={() => setLoading(true)}
          onLoadEnd={() => setLoading(false)}
          onError={() => setError(true)}
          onHttpError={() => setError(true)}
          originWhitelist={["https://*"]}
          allowsInlineMediaPlayback={true}
          mediaPlaybackRequiresUserAction={false}
          javaScriptEnabled={true}
          domStorageEnabled={true}
        />
      ) : (
        <View style={styles.errorContainer}>
          <Text style={styles.errorIcon}>⚠️</Text>
          <Text style={styles.errorTitle}>Connection Error</Text>
          <Text style={styles.errorText}>
            Unable to connect to HireSense AI servers. Please check your internet connection or try again later.
          </Text>
          <TouchableOpacity style={styles.button} onPress={handleReload}>
            <Text style={styles.buttonText}>Retry Connection</Text>
          </TouchableOpacity>
        </View>
      )}

      {URL_IS_CONFIGURED && loading && !error && (
        <View style={styles.loaderContainer}>
          <Image
            source={require("./assets/hiresense-ai-logo.png")}
            style={styles.logo}
            resizeMode="contain"
            accessibilityLabel="HireSense AI"
          />
          <ActivityIndicator size="large" color="#22d3ee" />
          <Text style={styles.loaderText}>Loading HireSense AI...</Text>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#07101f',
  },
  webview: {
    flex: 1,
    backgroundColor: '#07101f',
  },
  loaderContainer: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#07101f',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 15,
  },
  loaderText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 30,
    backgroundColor: '#07101f',
  },
  logo: {
    width: 280,
    height: 115,
    marginBottom: 10,
  },
  errorIcon: {
    fontSize: 48,
    marginBottom: 15,
  },
  errorTitle: {
    color: '#ffffff',
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 10,
  },
  errorText: {
    color: '#aaaaaa',
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 25,
  },
  button: {
    backgroundColor: '#7c5cff',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 25,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
});
