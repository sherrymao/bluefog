import copy
import os
import shlex
import subprocess
import sys
import textwrap
import traceback


from distutils.errors import CompileError, \
    DistutilsPlatformError, DistutilsSetupError, LinkError
from distutils.version import LooseVersion

from setuptools import find_packages, setup, Extension
from setuptools.command.build_ext import build_ext as _build_ext


# Package meta-data.
NAME = "bluefog"
DESCRIPTION = ""
EMAIL = "bichengying@gmail.com"
AUTHOR = "Bicheng Ying"
REQUIRES_PYTHON = ">=3.7.0"
VERSION = "0.1.0"

EXTRAS = {}


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    lic = f.read()

with open('requirements.txt') as f:
    reqs = list(f.read().strip().split('\n'))


bluefog_tensorflow_mpi_lib = Extension('bluefog.tensorflow.mpi_lib', [])
bluefog_torch_mpi_lib = Extension('bluefog.torch.mpi_lib', [])


def check_macro(macros, key):
    return any(k == key and v for k, v in macros)


def set_macro(macros, key, new_value):
    if any(k == key for k, _ in macros):
        return [(k, new_value if k == key else v) for k, v in macros]
    return macros + [(key, new_value)]


def test_compile(build_ext, name, code, libraries=None, include_dirs=None,
                 library_dirs=None,
                 macros=None, extra_compile_preargs=None,
                 extra_link_preargs=None):
    test_compile_dir = os.path.join(build_ext.build_temp, 'test_compile')
    if not os.path.exists(test_compile_dir):
        os.makedirs(test_compile_dir)

    source_file = os.path.join(test_compile_dir, '%s.cc' % name)
    with open(source_file, 'w') as src_f:
        src_f.write(code)

    compiler = build_ext.compiler
    [object_file] = compiler.object_filenames([source_file])
    shared_object_file = compiler.shared_object_filename(
        name, output_dir=test_compile_dir)

    compiler.compile([source_file], extra_preargs=extra_compile_preargs,
                     include_dirs=include_dirs, macros=macros)
    compiler.link_shared_object(
        [object_file], shared_object_file, libraries=libraries,
        library_dirs=library_dirs,
        extra_preargs=extra_link_preargs)

    return shared_object_file


def get_cpp_flags(build_ext):
    last_err = None
    default_flags = ['-std=c++11', '-fPIC', '-O2', '-Wall']
    if sys.platform == 'darwin':
        # Darwin most likely will have Clang, which has libc++.
        flags_to_try = [default_flags + ['-stdlib=libc++'],
                        default_flags]
    else:
        flags_to_try = [default_flags,
                        default_flags + ['-stdlib=libc++']]
    for cpp_flags in flags_to_try:
        try:
            test_compile(build_ext, 'test_cpp_flags',
                         extra_compile_preargs=cpp_flags,
                         code=textwrap.dedent('''\
                    #include <unordered_map>
                    void test() {
                    }
                    '''))

            return cpp_flags
        except (CompileError, LinkError):
            last_err = 'Unable to determine C++ compilation flags (see error above).'
        except Exception:  # pylint: disable=broad-except
            last_err = 'Unable to determine C++ compilation flags.  ' \
                       'Last error:\n\n%s' % traceback.format_exc()

    raise DistutilsPlatformError(last_err)


def get_link_flags(build_ext):
    last_err = None
    libtool_flags = ['-Wl,-exported_symbols_list']
    ld_flags = ['-Wl', "-stdlib=libc++"]
    flags_to_try = [ld_flags, libtool_flags]
    for link_flags in flags_to_try:
        try:
            test_compile(build_ext, 'test_link_flags',
                         extra_link_preargs=link_flags,
                         code=textwrap.dedent('''\
                    void test() {
                    }
                    '''))

            return link_flags
        except (CompileError, LinkError):
            last_err = 'Unable to determine C++ link flags (see error above).'
        except Exception:  # pylint: disable=broad-except
            last_err = 'Unable to determine C++ link flags.  ' \
                       'Last error:\n\n%s' % traceback.format_exc()

    raise DistutilsPlatformError(last_err)


def get_mpi_flags():
    show_command = os.environ.get('BLUEFOG_MPICXX_SHOW', 'mpicxx -show')
    try:
        mpi_show_output = subprocess.check_output(
            shlex.split(show_command), universal_newlines=True).strip()
        mpi_show_args = shlex.split(mpi_show_output)
        if not mpi_show_args[0].startswith('-'):
            # Open MPI and MPICH print compiler name as a first word, skip it
            mpi_show_args = mpi_show_args[1:]
        # strip off compiler call portion and always escape each arg
        return ' '.join(['"' + arg.replace('"', '"\'"\'"') + '"'
                         for arg in mpi_show_args])
    except Exception:
        raise DistutilsPlatformError(
            '%s failed (see error below), is MPI in $PATH?\n'
            'Note: If your version of MPI has a custom command to show compilation flags, '
            'please specify it with the BLUEFOG_MPICXX_SHOW environment variable.\n\n'
            '%s' % (show_command, traceback.format_exc()))


def get_cuda_dirs(build_ext, cpp_flags):
    cuda_include_dirs = []
    cuda_lib_dirs = []

    cuda_home = os.environ.get('BLUEFOG_CUDA_HOME')
    if cuda_home:
        cuda_include_dirs += ['%s/include' % cuda_home]
        cuda_lib_dirs += ['%s/lib' % cuda_home, '%s/lib64' % cuda_home]

    cuda_include = os.environ.get('BLUEFOG_CUDA_INCLUDE')
    if cuda_include:
        cuda_include_dirs += [cuda_include]

    cuda_lib = os.environ.get('BLUEFOG_CUDA_LIB')
    if cuda_lib:
        cuda_lib_dirs += [cuda_lib]

    if not cuda_include_dirs and not cuda_lib_dirs:
        # default to /usr/local/cuda
        cuda_include_dirs += ['/usr/local/cuda/include']
        cuda_lib_dirs += ['/usr/local/cuda/lib', '/usr/local/cuda/lib64']

    try:
        test_compile(build_ext, 'test_cuda', libraries=['cudart'],
                     include_dirs=cuda_include_dirs,
                     library_dirs=cuda_lib_dirs,
                     extra_compile_preargs=cpp_flags,
                     code=textwrap.dedent('''\
            #include <cuda_runtime.h>
            void test() {
                cudaSetDevice(0);
            }
            '''))
    except (CompileError, LinkError):
        raise DistutilsPlatformError(
            'CUDA library was not found (see error above).\n'
            'Please specify correct CUDA location with the BLUEFOG_CUDA_HOME '
            'environment variable or combination of BLUEFOG_CUDA_INCLUDE and '
            'BLUEFOG_CUDA_LIB environment variables.\n\n'
            'BLUEFOG_CUDA_HOME - path where CUDA include and lib directories can be found\n'
            'BLUEFOG_CUDA_INCLUDE - path to CUDA include directory\n'
            'BLUEFOG_CUDA_LIB - path to CUDA lib directory')

    return cuda_include_dirs, cuda_lib_dirs


def get_common_options(build_ext):
    cpp_flags = get_cpp_flags(build_ext)
    link_flags = get_link_flags(build_ext)

    try:
        mpi_flags = get_mpi_flags()
    except Exception:  # pylint: disable=broad-except
        raise DistutilsSetupError(
            'Cannot find MPI command. Is MPI installed or included in $PATH?'
            'Error: {}'.format(traceback.format_exc())
        )

    MACROS = []
    INCLUDES = []
    SOURCES = ["bluefog/common/common.cc",
               "bluefog/common/logging.cc",
               "bluefog/common/mpi_context.cc",
               "bluefog/common/mpi_controller.cc",
               "bluefog/common/operations.cc",
               "bluefog/common/tensor_queue.cc"]
    COMPILE_FLAGS = cpp_flags + shlex.split(mpi_flags)
    LINK_FLAGS = link_flags + shlex.split(mpi_flags)
    LIBRARY_DIRS = []
    LIBRARIES = []
    EXTRA_OBJECTS = []

    return dict(MACROS=MACROS,
                INCLUDES=INCLUDES,
                SOURCES=SOURCES,
                COMPILE_FLAGS=COMPILE_FLAGS,
                LINK_FLAGS=LINK_FLAGS,
                LIBRARY_DIRS=LIBRARY_DIRS,
                LIBRARIES=LIBRARIES,
                EXTRA_OBJECTS=EXTRA_OBJECTS)


def check_tf_version():
    try:
        import tensorflow
        if LooseVersion(tensorflow.__version__) < LooseVersion('1.1.0'):
            raise DistutilsPlatformError(
                'Your TensorFlow version %s is outdated.  '
                'Bluefog requires tensorflow>=1.1.0' % tensorflow.__version__)
    except ImportError:
        raise DistutilsPlatformError(
            'import tensorflow failed, is it installed?\n\n%s' % traceback.format_exc())


def build_tf_extension(build_ext, global_options):
    # Backup the options, preventing other plugins access libs that
    # compiled with compiler of this plugin
    options = copy.deepcopy(global_options)
    import tensorflow as tf

    tf_compile_flags = tf.sysconfig.get_compile_flags()
    tf_link_flags = tf.sysconfig.get_link_flags()
    have_cuda = tf.test.is_built_with_cuda()
    updated_macros = set_macro(
        options['MACROS'], 'HAVE_CUDA', str(int(have_cuda)))
    print(tf_compile_flags, tf_link_flags, have_cuda)

    if have_cuda:
        cuda_include_dirs, cuda_lib_dirs = get_cuda_dirs(
            build_ext, options['COMPILE_FLAGS'])
        options['INCLUDES'] += cuda_include_dirs
        options['LIBRARY_DIRS'] += cuda_lib_dirs
        options['LIBRARIES'] += ['cudart']
        print('INFO: Try Tensorflow extension with CUDA.')

    bluefog_tensorflow_mpi_lib.define_macros = updated_macros
    bluefog_tensorflow_mpi_lib.include_dirs = options['INCLUDES']
    bluefog_tensorflow_mpi_lib.sources = options['SOURCES'] + [
        "bluefog/tensorflow/adapter.cc"
    ]
    bluefog_tensorflow_mpi_lib.extra_compile_args = (
        options['COMPILE_FLAGS'] + tf_compile_flags)
    bluefog_tensorflow_mpi_lib.extra_link_args = (
        options['LINK_FLAGS'] + tf_link_flags)
    bluefog_tensorflow_mpi_lib.library_dirs = options['LIBRARY_DIRS']
    bluefog_tensorflow_mpi_lib.libraries = options['LIBRARIES']
    bluefog_tensorflow_mpi_lib.extra_objects = options['EXTRA_OBJECTS']

    build_ext.build_extension(bluefog_tensorflow_mpi_lib)


def dummy_import_torch():
    try:
        import torch  # pylint: disable=unused-import
    except:  # pylint: disable=bare-except
        pass


def check_torch_version():
    try:
        import torch
        if LooseVersion(torch.__version__) < LooseVersion('1.0.0'):
            raise DistutilsPlatformError(
                'Your PyTorch version %s is outdated.  '
                'Bluefog requires torch>=1.0.0' % torch.__version__)
    except ImportError:
        raise DistutilsPlatformError(
            'import torch failed, is it installed?\n\n%s' % traceback.format_exc())


def is_torch_cuda(build_ext, include_dirs, extra_compile_args):
    try:
        from torch.utils.cpp_extension import include_paths
        test_compile(build_ext, 'test_torch_cuda',
                     include_dirs=include_dirs + include_paths(cuda=True),
                     extra_compile_preargs=extra_compile_args,
                     code=textwrap.dedent('''\
            #include <THC/THC.h>
            void test() {
            }
            '''))
        return True
    except (CompileError, LinkError, EnvironmentError):
        print('INFO: Above error indicates that this PyTorch installation does not support CUDA.')
        return False


def build_torch_extension(build_ext, global_options):
    # Backup the options, preventing other plugins access libs that
    # compiled with compiler of this plugin
    options = copy.deepcopy(global_options)
    have_cuda = is_torch_cuda(build_ext, include_dirs=options['INCLUDES'],
                              extra_compile_args=options['COMPILE_FLAGS'])
    if have_cuda:
        cuda_include_dirs, cuda_lib_dirs = get_cuda_dirs(
            build_ext, options['COMPILE_FLAGS'])
        options['INCLUDES'] += cuda_include_dirs
        options['LIBRARY_DIRS'] += cuda_lib_dirs
        options['LIBRARIES'] += ['cudart']
        print('INFO: Try PyTorch extension with CUDA.')

    # Update HAVE_CUDA to mean that PyTorch supports CUDA.
    updated_macros = set_macro(
        options['MACROS'], 'HAVE_CUDA', str(int(have_cuda)))

    # Always set _GLIBCXX_USE_CXX11_ABI, since PyTorch can only detect whether it was set to 1.
    import torch
    updated_macros = set_macro(updated_macros, '_GLIBCXX_USE_CXX11_ABI',
                               str(int(torch.compiled_with_cxx11_abi())))

    # PyTorch requires -DTORCH_API_INCLUDE_EXTENSION_H
    updated_macros = set_macro(
        updated_macros, 'TORCH_API_INCLUDE_EXTENSION_H', '1')

    if have_cuda:
        from torch.utils.cpp_extension import CUDAExtension as TorchExtension
    else:
        # CUDAExtension fails with `ld: library not found for -lcudart` if CUDA is not present
        from torch.utils.cpp_extension import CppExtension as TorchExtension

    ext = TorchExtension(bluefog_torch_mpi_lib.name,
                         define_macros=updated_macros,
                         include_dirs=options['INCLUDES'],
                         sources=options['SOURCES'] + [
                             "bluefog/torch/adapter.cc",
                             "bluefog/torch/cuda_util.cc",
                             "bluefog/torch/handle_manager.cc",
                             "bluefog/torch/mpi_ops.cc",
                             "bluefog/torch/mpi_win_ops.cc"
                         ],
                         extra_compile_args=options['COMPILE_FLAGS'],
                         extra_link_args=options['LINK_FLAGS'],
                         library_dirs=options['LIBRARY_DIRS'],
                         libraries=options['LIBRARIES'])

    # Patch an existing bluefog_torch_mpi_lib extension object.
    for k, v in ext.__dict__.items():
        bluefog_torch_mpi_lib.__dict__[k] = v

    build_ext.build_extension(bluefog_torch_mpi_lib)


class custom_build_ext(_build_ext):
    # run the customize_compiler
    def build_extensions(self):
        options = get_common_options(self)
        built_plugins = []

        # If PyTorch is installed, it must be imported before others, otherwise
        # we may get an error: dlopen: cannot load any more object with static TLS
        if not os.environ.get('BLUEFOG_WITHOUT_PYTORCH'):
            dummy_import_torch()

        if not os.environ.get('BLUEFOG_WITHOUT_TENSORFLOW'):
            try:
                check_tf_version()
                build_tf_extension(self, options)
                built_plugins.append(True)
                print('INFO: Tensorflow extension is built successfully.')
            except: # pylint: disable=bare-except
                if not os.environ.get('BLUEFOG_WITHOUT_TENSORFLOW'):
                    print(
                        'INFO: Unable to build TensorFlow plugin, will skip it.\n\n'
                        '%s' % traceback.format_exc(), file=sys.stderr)
                    built_plugins.append(False)
                else:
                    raise

        if not os.environ.get('BLUEFOG_WITHOUT_PYTORCH'):
            try:
                check_torch_version()
                build_torch_extension(self, options)
                built_plugins.append(True)
                print('INFO: PyTorch extension is built successfully.')
            except:  # pylint: disable=bare-except
                if not os.environ.get('BLUEFOG_WITHOUT_PYTORCH'):
                    print('INFO: Unable to build PyTorch plugin, will skip it.\n\n'
                          '%s' % traceback.format_exc())
                    built_plugins.append(False)
                else:
                    raise


setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=readme,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    packages=find_packages(exclude=["test", "obselete"]),
    include_package_data=True,
    license=lic,
    classifiers=[
        "License :: OSI Approved :: Apache Software License"
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    ext_modules=[bluefog_torch_mpi_lib, bluefog_tensorflow_mpi_lib],
    cmdclass={"build_ext": custom_build_ext},
    install_requires=reqs,
    extras_require=EXTRAS,
)