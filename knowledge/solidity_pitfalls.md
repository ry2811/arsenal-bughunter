# Advanced Solidity Security Pitfalls

A curated list of compiler-specific and deep technical pitfalls for Senior Auditors.

## 1. PUSH0 (EIP-3855) & EVM Version Mismatch
- **Details:** Solidity `0.8.20+` uses the `PUSH0` opcode.
- **Vulnerability:** Deploying `0.8.20+` on L2s (Arbitrum, Linea, Optimism) or chains that do NOT support `PUSH0` will cause a contract revert.
- **Audit Check:** Check `foundry.toml` [evm_version] or individual compiler settings.

## 2. Reentrancy with `transfer` or `send` (The 2300 Gas Trap)
- **Details:** Using `addr.transfer()` or `addr.send()` limits gas to 2300.
- **Modern Issue:** Chain updates (like Istanbul EIP-1884) or L2-specific gas costs (Gnosis Safe, Proxy accounts) can cause these to fail, leading to **denial-of-service** on withdrawals.
- **Audit Check:** Always use `(bool success, ) = addr.call{value: val}("")`.

## 3. Implicit Upgradability Issues
- **Uninitialized Proxies:** Always check if `_disableInitializers()` is called in the constructor of implementation contracts.
- **Storage Collisions:** Ensure inherited contracts don't accidentally shadow storage slots.

## 4. Arithmetic Precision & Overflow
- **Division before Multiplication:** Always check for precision loss.
- **Rounding Direction:** Ensure Vaults round "down" in favor of the protocol and "up" in favor of the user (where applicable).
