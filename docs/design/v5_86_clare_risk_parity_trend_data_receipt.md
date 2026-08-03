# V5.86 Clare risk-parity trend data receipt

## Admission

The exact eight-symbol adjusted-close contract is admitted after the frozen
protocol commit 5d95631 and the narrow URTH allowlist commit dbbef4b, before a
V5.86 engine existed or any candidate return, metric, ranking, gate, or route
was computed or inspected.

- Frozen protocol SHA-256:
  b457cd6704f61f5332edce25ba357303e55245dd878de03c0420b80aedcfacd4.
- Outcome-blind data-manifest SHA-256:
  303f5827113a304b5262d7920de25c3d80482d03fbba8f2e4e329e1ba43c78cd.
- Combined canonical SHA-256:
  72dbc83f4523f9e003a0fce87add0f6c341edaec3efdeafce90e9a17d6d133a2.

## Provider, mapping, and adjustment semantics

- Provider: authenticated Tiingo End-of-Day read-only HTTPS API.
- Provider field: adjClose normalized to adjusted_close.
- Semantics: provider split- and dividend-adjusted closing price.
- Exact identity mappings: URTH,VWO,BND,DBC,VNQ,BIL,SPY,IEF.
- URTH was requested once for 2012-01-10 through 2026-07-31 through the
  destination-allowlisted GET-only repository adapter.
- First returned URTH session: 2012-01-12; exact last session: 2026-07-31.
- The other seven histories were reused only from already admitted, pinned
  V5.72, V5.73, V5.74, and V5.75 canonical evidence.
- No manual CSV, hand-normalized bar, synthetic history, broker data,
  adjusted-OHLCV claim, point-in-time vintage claim, or execution-price claim
  exists.

URTH acquisition evidence:

- accepted rows: 3,658;
- raw response SHA-256:
  8611826c94fad8585a79b023fcb32f1af4a61883d974384220023a004a9663d5;
- canonical SHA-256:
  9d10457b2689271b00706dc6782b1ba7b8b412c186f9e7102da90999ea2a36ea;
- sanitized refresh-manifest SHA-256:
  0a459b9ad80a74a67de587451857a2fe206ccbd2a7fbf048911ec6b30f37e036;
- destination allowlist enforced: true;
- method allowlist: GET only;
- token value printed, written, or recorded: false.

## Exact canonical coverage and hashes

Every symbol contains the identical 3,658-session sequence from 2012-01-12
through 2026-07-31. The combined file contains 29,264 rows.

| Symbol | Source-file SHA-256 | Normalized-symbol SHA-256 |
| --- | --- | --- |
| URTH | 9d10457b2689271b00706dc6782b1ba7b8b412c186f9e7102da90999ea2a36ea | fe3cbd4216baec0f425845b6017b15562c4f65fb0ed55d60dcd9af28e707ccbd |
| VWO | bf64f49465efdf0e7206022f25a7b1fd7268339055f2163456f156894e9a9b2b | 06ee92cbc7988708438c437e3ad8a272bd1d06c8ab26e033462a5c6f85419579 |
| BND | 2d531b6655b8fd06d08ccb8b56b83442235cc503b6763771fe94eacf85676182 | a55d716a593efb62dfc777c3051adda2fc7d305bd509f9df60031417443a3ac8 |
| DBC | 8720fa2256e971ae5004b5fb92d095d699d122fe68d51f37d61a9665cb8054b1 | 054762fa6404d6fedcae8c1c9d4836fd91f707754d01b7965f9b75e003bdee6a |
| VNQ | 3ea541bde00148955b1f5185a0650921b4bf0ef25defc2ce921565d1a3b11d68 | c6f0a75d874531975b0e8356f0d878a2e64e114dc663c343fc867a9be3ba2d9a |
| BIL | 8d45ab5e0a0ebeeb8447b2e12b368f631b91fe97bd3b3fdc736bda391b8753c5 | 8377ea544a635e17732d1427fe0d12ddf7836f7ec57e8f89fcd8730a0705ab10 |
| SPY | 5a4d8c0fea3ca879011239067f76c6375012f30835e0d579f329f018176b77e2 | 2bc9bfa3180d35e5a8cb7e79fcc7df4e4c72d964a1ffb1ef530fb3368d593631 |
| IEF | 091989173cb245146cfa2ffb88dcdf3e4f728a4e2ab753e191221b518596e56f | ade4c63ec2c2175235db6a2944d0c36a892eb501a0f9272231ca4138eee9a464 |

SPY's source-file hash is the pinned V5.72 multi-symbol canonical file; its
normalized-symbol hash proves the exact selected SPY series. Duplicate,
missing, invalid, nonpositive, stale, substituted, or session-mismatched rows:
none.

## Frozen chronology coverage

| Window | Sessions | First | Last |
| --- | ---: | --- | --- |
| warm-up/reference | 1,060 | 2012-01-12 | 2016-03-31 |
| full post-publication OOS | 2,598 | 2016-04-01 | 2026-07-31 |
| fold 1 | 881 | 2016-04-01 | 2019-09-30 |
| fold 2 | 882 | 2019-10-01 | 2023-03-31 |
| fold 3 | 835 | 2023-04-03 | 2026-07-31 |

The folds are disjoint and total exactly 2,598 sessions. Warm-up contains more
than the required 13 consecutive month-end levels. No return, score, parameter
selection, outcome rank, or gate decision was computed during admission.

## Credential, network, and safety receipt

- Writer-worktree .env present: false.
- Primary-checkout .env present: true.
- Process paper profile loaded before offline work: false.
- Process live profile loaded: false.
- Process broker credential alias count: zero.
- Ambient Tiingo credential loaded: false.
- Trusted child adapter loaded only TIINGO_API_KEY from the primary-checkout
  .env for the one URTH request.
- Credential value requested from the operator, printed, returned, persisted,
  or placed in a command/artifact: false.
- Network operations: exactly one allowlisted HTTPS GET to api.tiingo.com.
- Broker credential lookup, broker/account/order/position access, broker
  mutation, paper mutation, NexusTrade mutation, and live activity: false.
- Candidate outcome metrics computed or candidate ranking performed: false.

Generated raw response, canonical inputs, combined panel, and manifest remain
ignored under runs/v5_86_clare_risk_parity_trend. They contain no credential
value and are evidence bytes, not authority.

## Computation gate

The V5.86 engine must pin this receipt, the protocol, the combined canonical
file, and the outcome-blind manifest before reading prices. It must prove the
exact symbol/session/window identities and causal lag before producing any
performance result. Any mismatch blocks.