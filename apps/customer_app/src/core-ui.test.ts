import { describe, expect, it } from "vitest";
import { egp } from "./utils/format";
import { mediaUri } from "./utils/media";
import { loadConfig } from "./config/env";
describe("core UI helpers",()=>{it("formats EGP minor units",()=>{expect(egp(18000)).toBe("180 ج");expect(egp(18050)).toBe("180.50 ج")});it("requires https in staging",()=>{expect(()=>loadConfig({EXPO_PUBLIC_BAYTNA_ENV:"staging",EXPO_PUBLIC_BAYTNA_API_BASE_URL:"http://example.com"} as NodeJS.ProcessEnv)).toThrow()});});
