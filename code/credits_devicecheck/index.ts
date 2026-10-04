import ZelbiDeviceCheckModule from './src/ZelbiDeviceCheckModule';

/** False on Android, web, the simulator, and any build without this native module. */
export function isSupported(): boolean {
  try {
    return ZelbiDeviceCheckModule?.isSupported() ?? false;
  } catch {
    return false;
  }
}

/** A fresh single-use DeviceCheck token, base64 with no line breaks. Call only when isSupported(). */
export function generateToken(): Promise<string> {
  if (ZelbiDeviceCheckModule == null) {
    return Promise.reject(new Error('DeviceCheck is not available'));
  }
  return ZelbiDeviceCheckModule.generateToken();
}
