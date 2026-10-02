# Upstream attribution

ComplaintIQ adapts UI/workflow ideas from [MohammedHssan11/complaint-routing-intelligence](https://github.com/MohammedHssan11/complaint-routing-intelligence), inspected at commit `4be52e1004dc3c621c522d651759accbd78223dc`. Upstream saved pickle files are not executed or used as our trained model. Our additions include local model integration, data preparation, evaluation, persistence, and application changes.

Upstream MIT notice preserved verbatim:

```text
MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```

CFPB data provenance is recorded in data/manifest.json. Model weights are obtained separately and retain their licenses; Qwen3-4B-Instruct-2507 is Apache-2.0. No weights are bundled.
