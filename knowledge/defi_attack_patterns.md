# Advanced DeFi Attack Patterns (2024-2026)

Recognizing patterns from real-world high-impact exploits.

## 1. Oracle Logic & Flashloan Attacks
- **Pattern:** Using low-liquidity pool balances (DEX) as a price source.
- **Vulnerability:** Attacks use flashloans to inflate pool prices and borrow more assets than they are worth.
- **Audit Check:** Check for **Chainlink (AggregatorV3)** vs. **Spot (Uniswap Pool)** as the price source. Ensure `latestRoundData()` is validated (stale checks).

## 2. Reentrancy (Cross-contract & Read-only)
- **Cross-contract:** Entering through a different entry point (A calls B; B calls back to C).
- **Read-only Reentrancy:** Exploiting pool math when prices are "mid-transaction" and haven't updated yet.
- **Audit Check:** Look for `nonReentrant` modifiers on ALL public state-changing functions.

## 3. Signature & Permit Malleability
- **Pattern:** Using `ecrecover` or `Permit2` without proper nonce or deadline checks.
- **Vulnerability:** Reusing a valid signature to bypass authorization.
- **Audit Check:** Ensure EIP-712 is implemented correctly and signatures are invalidated after use.

## 4. Bridge & Governance Attacks
- **Bridging:** Check for cross-chain message passing logic. 
- **Governance:** Vulnerabilities where a huge loan can "swing" a vote to malicious proposals.
