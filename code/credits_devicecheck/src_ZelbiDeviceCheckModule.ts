import { NativeModule, requireOptionalNativeModule } from 'expo';
import { Platform } from 'react-native';

declare class ZelbiDeviceCheckModule extends NativeModule {
  isSupported(): boolean;
  generateToken(): Promise<string>;
}

// iOS only. Optional so Android, web and any build compiled before this module return
// null here instead of throwing at import.
export default Platform.OS === 'ios'
  ? requireOptionalNativeModule<ZelbiDeviceCheckModule>('ZelbiDeviceCheck')
  : null;
