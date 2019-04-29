cd aiortc
python setup.py build_ext --include-dirs="%~dp0include" --library-dirs="%~dp0lib\x64\Debug"
python setup.py develop
cd ..

