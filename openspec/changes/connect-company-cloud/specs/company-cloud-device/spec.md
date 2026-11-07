## ADDED Requirements

### Requirement: confidential material and credential handling

Device-side code, the vendor material and its test vectors SHALL be kept out of the public repository. Real credentials (device secret, access tokens, SIP password, Wi-Fi password, factory credentials) SHALL only be stored in git-ignored local configuration on PC or in protected storage on the board, and SHALL NOT appear in source code, logs, screenshots or plan documents.

#### Scenario: logging a signed request

- **WHEN** the device logs an outgoing authenticated request or its failure
- **THEN** the log contains the stage, request ID and error code, and does not contain authorization headers, secrets or passwords

### Requirement: algorithm conformance before network access

The device implementation SHALL reproduce every public test vector in the vendor material byte for byte (request signing, provisioning QR decoding with CRC check, talkback frame header) before it is used against any company environment.

#### Scenario: corrupted provisioning QR code

- **WHEN** the device scans a provisioning QR code whose CRC does not match
- **THEN** it rejects the code, logs a CRC error stage, and does not attempt to join Wi-Fi or call the provisioning API

### Requirement: provisioning and token lifecycle

The device SHALL synchronize time before its first signed request, complete provisioning to obtain a provisioning token, reach READY through heartbeat once GB28181 registration and media are ready, and refresh its token by signed request before expiry. It SHALL use only the provisioning or formal token permitted for each interface.

#### Scenario: heartbeat after READY

- **WHEN** a heartbeat response in the formal stage carries no `ready` field
- **THEN** the device keeps its READY state and does not restart provisioning

### Requirement: GB28181 live streaming

The device SHALL register to the company GB28181 gateway with the configuration it fetches from the service, answer device information and catalog queries with the issued device and channel IDs, and on INVITE stream PS-over-RTP H.264 using the transport and connection role negotiated in the SDP. After BYE or network loss it SHALL release the media session without leftovers.

#### Scenario: gateway requests TCP passive mode

- **WHEN** the gateway SDP requests TCP RTP with the device actively connecting
- **THEN** the device opens the TCP connection to the address in the SDP and sends framed RTP, rather than falling back to UDP

### Requirement: honest capability reporting

On every control-channel connection the device SHALL report a capability as `true` only if it is implemented and accepted; simulator stubs SHALL be labelled as stubs in acceptance records. Every control response SHALL echo the request ID and, where present, the app session ID.

#### Scenario: unsupported command

- **WHEN** the device receives a control command whose capability it did not report
- **THEN** it replies with an explicit error and does not report success

### Requirement: event video upload

The device SHALL upload event clips within the service limits using an event ID that stays the same across retries, SHALL never upload different content under an existing event ID, and SHALL keep a bounded local queue with backoff and expiry. Structured algorithm results SHALL stay in the local outbox until the company defines an interface for them.

#### Scenario: upload retried after network loss

- **WHEN** an upload fails because the network dropped and later succeeds on retry with the same file
- **THEN** the retry uses the same event ID and the service returns the original record as a duplicate

### Requirement: revocation

When the service reports that the device is unbound or its access is revoked, the device SHALL stop uploads, control handling and SIP sessions tied to the old binding and SHALL discard queued items that belong to the old owner.

#### Scenario: rebinding to a new account

- **WHEN** the device is unbound and later bound to a new account
- **THEN** no clip recorded under the old binding is uploaded to the new account
