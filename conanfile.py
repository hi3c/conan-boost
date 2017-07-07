from conans import ConanFile, tools
from conans.errors import ConanException
import os


class BoostConan(ConanFile):
    name = "boost"
    version = "1.64.0_2"
    license = "BSL"
    url = "http://boost.org"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = "shared=False"
    generators = "cmake"
    short_paths = True
    ios_archs = ("armv7", "arm64", "x86_64", "i386")
    requires = "multibuilder/1.0@hi3c/experimental"

    def source(self):
        tools.download("https://dl.bintray.com/boostorg/release/1.64.0/source/boost_1_64_0.zip",
                       "boost.zip")
        tools.unzip("boost.zip", keep_permissions=True)
        os.remove("boost.zip")

    @staticmethod
    def boost_arch(arch):
        if arch.startswith("x86") or arch.startswith("i386"): return "x86"
        if arch.startswith("arm") or arch.startswith("aarch"): return "arm"
        raise ConanException("Unknown arch: " + arch)

    @staticmethod
    def boost_addr_model(arch):
        if arch == "x86_64" or arch == "arm64": return "64"
        return "32"

    @property
    def boost_target_os(self):
        os = str(self.settings.os).lower()
        if os == "macos": return "darwin"
        if os == "ios": return "iphone"
        return os

    def build(self):
        vcvars = ""
        bootstrap = "./bootstrap.sh"
        if self.settings.os == "Windows":
            bootstrap = "bootstrap"

        env = {"SDKROOT": "", "CC": "", "CXX": "", "CFLAGS": "", "CXXFLAGS": "", "LDFLAGS": ""}
        with tools.environment_append(env):
            self.run("cd boost_1_64_0 && {vcvars}{bootstrap}".format(vcvars=vcvars, bootstrap=bootstrap))

        if self.settings.arch == "universal":
            with tools.pythonpath(self):
                from multibuilder import MultiBuilder
                self.multi_builder = MultiBuilder(self, self.ios_archs)
                self.multi_builder.no_chdir = True
                self.multi_builder.multi_build(self.real_build)
                return
        
        self.real_build(str(self.settings.arch))

    def write_user_config(self):
        compiler = str(self.settings.compiler).lower().replace("apple-", "")

        flags = os.environ.get("CXXFLAGS", "").split(" ")
        ldflags = os.environ.get("LDFLAGS", "").split(" ")

        if self.settings.os == "Macos":
            ldflags.append("-headerpad_max_install_names")

        # remove unecssary warnings
        if compiler == "clang": flags.append("-Wno-unused-local-typedef")

        compileflags = "" #"" ".join(["<compileflags>" + a for a in flags])
        linkflags = " ".join(["<linkflags>" + a for a in ldflags])

        with open(os.path.join("boost_1_64_0", "tools", "build", "src", "user-config.jam"), "w") as user:
            d = {
              "compiler": compiler,
              "cxx": os.path.join(self.conanfile_directory, "boost-compiler"),
              "compileflags": compileflags,
              "linkflags": linkflags,
              "os": str(self.settings.os).lower()
            }
            user.write(
              ("import option ;\nusing {compiler} : : {cxx} : {compileflags} {linkflags} ;\noption.set keep-going : false ;\n".format(**d)))

        with open(os.path.join(self.conanfile_directory, "boost-compiler"), "w") as bcomp:
            bcomp.write("#!/bin/sh\n{cxx} $@ {cflags}\n".format(cxx=os.environ.get("CXX", "c++"), cflags=" ".join(flags)))

        os.chmod(os.path.join(self.conanfile_directory, "boost-compiler"), 0755)

        return compiler

    def real_build(self, arch, triple):
        flags = ["--with-filesystem",
                 "--with-system",
                 "--abbreviate-paths",
                 "--stagedir=" + os.path.join(self.conanfile_directory, "build-" + arch),
                 "-j" + str(tools.cpu_count())]

        if self.settings.compiler == "Visual Studio":
            flags.append("toolset=msvc-{}.0".format(self.settings.compiler.version))
        else:
            flags.append("toolset=" + self.write_user_config())

        flags.append("link={}".format("static" if not self.options.shared else "shared"))
        if self.settings.compiler == "Visual Studio" and self.settings.compiler.runtime:
            flags.append("runtime-link={}".format("static" if "MT" in str(self.settings.compiler.runtime) else "shared"))
        flags.append("variant={}".format(str(self.settings.build_type).lower()))
        flags.append("address-model=" + self.boost_addr_model(arch))
        flags.append("target-os=" + self.boost_target_os)
        flags.append("architecture=" + self.boost_arch(arch))

        cmd = "cd boost_1_64_0 && {} {}".format(os.path.join(self.conanfile_directory, "boost_1_64_0", "b2"), " ".join(flags))
        self.output.info("Running: " + cmd)
        self.run(cmd)

    def package(self):
        self.copy("*.lib", dst="lib", keep_path=False)
        self.copy("*.a", dst="lib", src="build-universal", keep_path=False)

        if self.options.shared:
            self.copy("*.dll", dst="bin", keep_path=False)
            self.copy("*.so", dst="lib", src="build-univernal", keep_path=False)
            self.copy("*.dylib", dst="lib", src="build-univernal", keep_path=False)

        self.copy("*.hpp", src=os.path.join("boost_1_64_0", "boost"), dst="include/boost", keep_path=True)
        self.copy("*.h", src=os.path.join("boost_1_64_0", "boost"), dst="include/boost", keep_path=True)
        self.copy("*.ipp", src=os.path.join("boost_1_64_0", "boost"), dst="include/boost", keep_path=True)

    def package_info(self):
        if self.options.shared:
            self.cpp_info.defines.append("BOOST_ALL_DYN_LINK")
        else:
            self.cpp_info.defines.append("BOOST_USE_STATIC_LIBS")

        libs = ("filesystem", "system")

        if self.settings.compiler != "Visual Studio":
            self.cpp_info.libs = ["boost_" + lib for lib in libs]
        else:
            win_libs = []
            # http://www.boost.org/doc/libs/1_55_0/more/getting_started/windows.html
            visual_version = int(str(self.settings.compiler.version)) * 10
            runtime = "mt" # str(self.settings.compiler.runtime).lower()

            abi_tags = []
            if self.settings.compiler.runtime in ("MTd", "MT"):
                abi_tags.append("s")

            if self.settings.build_type == "Debug":
                abi_tags.append("gd")

            abi_tags = ("-%s" % "".join(abi_tags)) if abi_tags else ""

            version = "_".join(self.version.split(".")[0:2])
            suffix = "vc%d-%s%s-%s" %  (visual_version, runtime, abi_tags, version)
            prefix = "lib" if not self.options.shared else ""

            win_libs.extend(["%sboost_%s-%s" % (prefix, lib, suffix) for lib in libs])

            self.cpp_info.libs.extend(win_libs)
            self.cpp_info.defines.extend(["BOOST_ALL_NO_LIB"]) # DISABLES AUTO LINKING! NO SMART AND MAGIC DECISIONS THANKS!
