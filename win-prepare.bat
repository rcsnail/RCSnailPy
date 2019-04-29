#@REM pip install --global-option=build_ext --global-option="-IC:\tools\ffmpeg\include" --global-option="-IC:\tools\libsrtp" --global-option="-IC:\tools\opusfile-v0.9-win32" --global-option="-LC:\tools\ffmpeg\lib" --global-option="-LC:\tools\libsrtp\lib" --global-option="-LC:\tools\opusfile-v0.9-win32" aiortc

pip install --global-option="-I%~dp03rdparty\include" --global-option="-L%~dp03rdparty\lib\x64\Debug" --global-option=build_ext aiortc
