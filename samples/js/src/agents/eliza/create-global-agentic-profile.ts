import os from "os";
import { join } from "path";
import {
    createAgenticProfile,
    prettyJson,
    webDidToUrl
} from "@agentic-profile/common";
import {
    createEdDsaJwk,
    postJson
} from "@agentic-profile/auth";
import { saveProfile } from "./universal-auth.js";


(async ()=>{
    const services = [
        {
            name: "Business networking connector",
            type: "A2A",
            id: "connect",
            url: `httsp://example.com/agents/connect`
        }
    ];
    const { profile, keyring, b64uPublicKey } = await createAgenticProfile({ services, createJwkSet: createEdDsaJwk });

    try {
        // publish profile to web (so did:web:... will resolve)
        const { data } = await postJson(
            "https://testing.agenticprofile.ai/agentic-profile",
            { profile, b64uPublicKey }
        );
        const savedProfile = data.profile;
        const did = savedProfile.id;
        console.log( `Published demo user agentic profile to:

    ${webDidToUrl(did)}

Or via DID at:

    ${did}
`);

        // also save locally for reference
        const dir = join( os.homedir(), ".agentic", "iam", "a2a-demo-user" );
        await saveProfile({ dir, profile: savedProfile, keyring });

        console.log(`Saved demo user agentic profile to ${dir}

Shhhh! Keyring for testing... ${prettyJson( keyring )}`);
    } catch (error) {
        console.error( "Failed to create demo user profile", error );
    }
})();