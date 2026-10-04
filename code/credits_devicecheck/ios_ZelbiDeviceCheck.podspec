Pod::Spec.new do |s|
  s.name           = 'ZelbiDeviceCheck'
  s.version        = '1.0.0'
  s.summary        = 'Apple DeviceCheck token for the giveaway credit (D542 (4))'
  s.description    = 'Apple DeviceCheck token for the giveaway credit (D542 (4))'
  s.author         = ''
  s.homepage       = 'https://docs.expo.dev/modules/'
  s.platforms      = {
    :ios => '15.1'
  }
  s.source         = { git: '' }
  s.static_framework = true

  s.dependency 'ExpoModulesCore'
  s.frameworks = 'DeviceCheck'

  # Swift/Objective-C compatibility
  s.pod_target_xcconfig = {
    'DEFINES_MODULE' => 'YES',
  }

  s.source_files = "**/*.{h,m,mm,swift,hpp,cpp}"
end
