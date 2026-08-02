# V5.84 factor-momentum style data receipt

Status: admitted, outcome-blind, and frozen before engine implementation or any
candidate, control, comparator, composite, ranking, or performance inspection.

## Frozen bindings

- Protocol commit: `1a16754885f91b036bb9722ac1db60ffe6f7d264`
- Protocol SHA-256: `3ec0d6359cb4280e24a60fab8a9c04a18ac727f231fb89bd3526a9f0c4aa8361`
- Data-boundary commit: `a774f3698ae9b0aa9eabd87311c35197aa9dad04`
- Outcome-blind manifest: `runs/v5_84_factor_momentum_style_proxy/canonical_data_manifest.json`
- Manifest SHA-256: `ee0063bbb19f6c05b593b8519a0864d2224fe93061ca674f62412c736733d790`
- Combined canonical CSV: `runs/v5_84_factor_momentum_style_proxy/canonical_data.csv`
- Combined canonical SHA-256: `c54d53450cd523677e9f72a7a3ba001295c738a7a388b37ff2a3d1f5bf361919`

## Provenance and semantics

The bytes were acquired on 2026-08-02 by nine authenticated HTTPS GETs to the
repository-allowlisted Tiingo End-of-Day daily-price endpoint. Only the
existing `TIINGO_API_KEY` credential provider boundary was used. The provider
field `adjClose` was normalized as `adjusted_close`; the claim is Tiingo's
split- and dividend-adjusted close only. Adjusted OHLCV, executable prices,
point-in-time corporate-action vintage, index constituent history, and
survivorship-free exposures are not claimed.

The exact identity mappings are `IWD->IWD`, `IWF->IWF`, `RSP->RSP`, `VBR->VBR`,
`VIG->VIG`, `SPLV->SPLV`, `SHY->SHY`, `SPY->SPY`, and `IEF->IEF`. Every request
and admitted symbol begins on `2011-05-05` and ends on `2026-07-31`. All nine
symbols have the identical 3,832-session sequence. The combined snapshot has
34,488 rows, first common session `2011-05-05`, and last common session
`2026-07-31`.

## Per-symbol bindings

| Symbol | Rows | Canonical SHA-256 | Raw-response SHA-256 | Refresh-log SHA-256 | Normalized-series SHA-256 |
|---|---:|---|---|---|---|
| IWD | 3,832 | `828b4a71c7a787404fb6da7b6c19296495a33aa84c15c3461691e70ed396a106` | `2e687e86c0dba0cf0c3caf8242e86ad68a908ab9ca9f05ae9f939f9ab1fa72c4` | `2ca30418ae508143dc0c500195c7126de08f60e1b4c7754af42ca08316edb395` | `dd24fc7339746d03d87b4b3ea3cdba9f54ea6ce3f46b8bee6f7521729e50970b` |
| IWF | 3,832 | `05ab5f111af19f6b7567d13072e29e04540ad2cda5fc6342b5f85f8293635b20` | `5dcf74f1c38a610c83ff80aaeceef99e0e4a2f9ee58d4aedd85929e2331ec2ca` | `af4b35c5d44efc6c789b080c2316aa5b32f1b33ea450645f9944318862629ab8` | `c59f36f15081f52130677715107ce3d709a4da3ee2c72c363a6741c3248fe95f` |
| RSP | 3,832 | `286c1f1e5f12e5a4a6d713abff2b2842b97f13c62451baa71570394829900215` | `ed94e17b06fe86827d3e0fea44c481b54d9fcddece853077c24a8cb3406c60bf` | `6a2da80d991ffad5c97a31870e164fa78b0cb9f60df91c0e6582ddc0828c030d` | `05d011a8b94ccdaaef89987802a87aa69c6be96ccf2b63cc410b6f94ca893d3d` |
| VBR | 3,832 | `8962c290ae6c3ac3b5629f285e30a02c0ba6d9b7f8818b939ebad4683cac3d49` | `475a987a721bfa4f6d533f5f2ad34f3dc481e83aa6e5cba7be1fe3539eeba384` | `956bf585ea2567946427e6fcf0c7ce7258767776b52d4c633774b700a32b9639` | `0a9951e403258342c99c21e28916208a9d746d6fa038ab359baa830d662f28f1` |
| VIG | 3,832 | `1486607ba12f12cd382a3e3394c432e56c3a011d9da1754831c21711801ffc89` | `eec48d8ac1fc31785fc862941bc73463d61918eb1a988c7b754232e0d9034eb2` | `7419284c4f108717aa175a66b8762a0e821a757daaeb854b0b558c12cbfc38fb` | `faaf5c9577856a26c615272940eb47df6fa0340967d036508a3d9b302985c821` |
| SPLV | 3,832 | `582d0b0de55e82cf6fd8c64f3b76e896d7404a07fd5a196331f6cac388011891` | `2024410c83330b208bc9647cade5bc8a9fe4e340b6834acf3eba478a7358617c` | `7e40dc69658702a02cc16e78e65520c1fe5070f2b36ab24f4258fa08536085c1` | `937572e5029d87f518d4f54f9f1f6dbf23b22d862cc89698326813c6de7872a4` |
| SHY | 3,832 | `44096c0470618a8ec152f5cc600bc2ab5a2bdcca4e6020ef7e8fa60264c95b2a` | `cb21bc6e9210b9e7a60bcec6de64006c1dad2f806390ed7e047fa2914d177d29` | `dfa70f1658691732653c3f4decef9d81258f445a4c6b2a5837c3267774da1cf6` | `4aac1bb59bfb339576e65e0bc72d2b72d06970dec528250faa6f55b14a70b526` |
| SPY | 3,832 | `c91014fcd12bd0329bef911ceb24d779d13da085340fb7fc3e966624fa6806a8` | `58447e6775f8b639b0a410a158d042e75f5876c1baee0409fafd879d0cad1e73` | `b8823bcbbb4dca7f5af621a6e399507345917f44a694627968edee46c603e600` | `ee8e88f4ead6080c7379b5bf243d202f798c69b0e3b312843db51ac588b2ff2b` |
| IEF | 3,832 | `a5a30ecfd0e74f1de665a83825fff2a0f3c5bd463a7513028709098fd89e5581` | `19a404213b4cef77cf1b2cb66e8986f68fb3061d923462134c64ed315929553e` | `e17ba2c12adc620f97c247ba6e45361806028677a31974e2cb7354c8dd2263b7` | `4d0b1c5f852aed2f0c95641c8b3c52bcd4f34a88675d58c531aba0d752296e44` |

## Outcome-blind and safety state

At receipt creation, outcome metrics computed = false, candidate ranking
performed = false, broker access performed = false, paper mutation performed =
false, and live authorized = false. The market-data credential was available
and loaded inside the trusted adapter; its value was neither printed nor
persisted. Raw responses and canonical data remain ignored generated state and
are bound by the hashes above.
