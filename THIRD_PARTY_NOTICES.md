# Third-Party Software Notices and Information

This project, **Transkript**, is licensed under the MIT License (see [LICENSE](LICENSE)) and relies on open-source third-party libraries for its runtime functionality. This document lists the direct dependencies, their published licenses, and their compatibility assessment for distribution.

> **Disclaimer:** The information provided below represents a technical review of the published licenses of third-party software and does not constitute formal legal advice. Compatibility assessments reflect open-source best practices and standard industry understanding ("appears compatible based on the package's published license").

---

## Direct Runtime Dependencies

| Package | Version Tested | Published License | Source / Project | Compatibility Note |
| :--- | :--- | :--- | :--- | :--- |
| **faster-whisper** | `>=1.0.0` (1.2.1) | MIT License | [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Appears compatible with binary redistribution and commercial usage under standard MIT attribution requirements. |
| **CTranslate2** | `>=4.0.0` (4.8.1) | MIT License | [OpenNMT/CTranslate2](https://github.com/OpenNMT/CTranslate2) | Appears compatible with redistribution and commercial distribution. |
| **pywebview** | `>=5.0.0` (6.2.1) | BSD 3-Clause License | [r0x0d/pywebview](https://github.com/r0x0d/pywebview) | Appears compatible with binary redistribution under standard BSD copyright attribution requirements. |
| **PyAV (av)** | `>=12.0.0` (18.0.0) | BSD 3-Clause License | [PyAV-Org/PyAV](https://github.com/PyAV-Org/PyAV) | PyAV itself is BSD-3-Clause. Binary wheels on PyPI link dynamically with FFmpeg compiled under LGPL v2.1+, which appears compatible with dynamic linking without requiring source disclosure of the host application. |
| **psutil** | `>=5.9.0` (7.2.2) | BSD 3-Clause License | [giampaolo/psutil](https://github.com/giampaolo/psutil) | Appears compatible with redistribution under standard BSD notice requirements. |
| **numpy** | `>=1.24.0` | BSD 3-Clause License | [numpy/numpy](https://github.com/numpy/numpy) | Transitive dependency of faster-whisper/ctranslate2. Appears compatible. |

---

## Underlying Models & External Components

- **Whisper Models (OpenAI / Systran)**:
  - Model weights used by `faster-whisper` originate from OpenAI's Whisper model architecture, released under the **MIT License**.
  - Quantized CTranslate2 model weights (`Systran/faster-whisper-small`) are distributed under the **MIT License**.
- **Silero VAD**:
  - The voice activity detection component integrated within `faster-whisper` is licensed under the **MIT License**.
- **Microsoft Edge WebView2 Runtime**:
  - System component on modern Windows 10/11 operating systems. Installed and serviced by Microsoft.

---

## Intellectual Property & Independent Architecture Notice

- **motion-web**:
  - `motion-web` is **NOT** a dependency of this project.
  - No source code, shaders, styles, assets, SVG paths, physics parameters, or layouts from `motion-web` or any other non-commercially restricted project are used or present in this repository.
  - The UI and motion system in `ui/` are 100% original vanilla HTML5, CSS3, and JavaScript, designed independently for this application.
