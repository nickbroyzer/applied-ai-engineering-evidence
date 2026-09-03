import { Linking, Platform } from 'react-native';

/** Opens the platform maps app for turn-by-turn directions to the given
 * coordinates. iOS tries the Apple Maps URL scheme first, falling back to the
 * universal maps.apple.com link; Android tries the google.navigation intent
 * first, falling back to the universal Google Maps directions link. */
export async function openDirections(
  lat: number,
  lng: number,
  _label?: string,
): Promise<void> {
  if (Platform.OS === 'ios') {
    const appleUrl = `maps://?daddr=${lat},${lng}`;
    const canOpenApple = await Linking.canOpenURL(appleUrl);
    if (canOpenApple) {
      await Linking.openURL(appleUrl);
      return;
    }
    const fallback = `https://maps.apple.com/?daddr=${lat},${lng}`;
    await Linking.openURL(fallback);
    return;
  }

  const androidUrl = `google.navigation:q=${lat},${lng}`;
  const canOpenAndroid = await Linking.canOpenURL(androidUrl);
  if (canOpenAndroid) {
    await Linking.openURL(androidUrl);
    return;
  }
  const fallback = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
  await Linking.openURL(fallback);
}
