// This file is a wrapper that runs all individual proxy tests.
// It is maintained for compatibility with scripts like `bun test:proxy`.

import "./test/public";
import "./test/mtls";
import "./test/signature";
import "./test/unauthorized";
