import DeviceCheck
import ExpoModulesCore

// D542 (4): the giver's iPhone check for a giveaway credit. DCDevice needs no entitlement,
// only a registered app ID. It is unsupported on the simulator.
public class ZelbiDeviceCheckModule: Module {
  public func definition() -> ModuleDefinition {
    Name("ZelbiDeviceCheck")

    Function("isSupported") {
      return DCDevice.current.isSupported
    }

    // Apple requires the token base64-encoded with no line breaks; no options means none.
    AsyncFunction("generateToken") { () async throws -> String in
      let token = try await DCDevice.current.generateToken()
      return token.base64EncodedString()
    }
  }
}
