from conans import ConanFile, tools
import os


class BoostConan(ConanFile):
    name = "boost"
    version = "1.64.0"
    license = "BSL"
    url = "http://boost.org"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = "shared=False"
    generators = "cmake"
    short_paths = True

    def source(self):
        tools.download("https://dl.bintray.com/boostorg/release/1.64.0/source/boost_1_64_0.zip",
                       "boost.zip")
        tools.unzip("boost.zip")
        os.remove("boost.zip")

    def build(self):
        vcvars = ""
        bootstrap = "./bootstrap.sh"
        if self.settings.os == "Windows":
            #vcvars = "&&" + tools.vcvars_command(self.settings)
            bootstrap = "bootstrap"

        self.run("cd boost_1_64_0 && {vcvars}{bootstrap}".format(vcvars=vcvars, bootstrap=bootstrap))

        flags = ["--with-filesystem",
                 "--with-system",
                 "--abbreviate-paths",
                 "-j" + str(tools.cpu_count())]

        if self.settings.compiler == "Visual Studio":
            flags.append("toolset=msvc-{}.0".format(self.settings.compiler.version))
        elif str(self.settings.compiler) in ["clang", "gcc"]:
            flags.append("toolset={}".format(self.settings.compiler))

        flags.append("link={}".format("static" if not self.options.shared else "shared"))
        if self.settings.compiler == "Visual Studio" and self.settings.compiler.runtime:
            flags.append("runtime-link={}".format("static" if "MT" in str(self.settings.compiler.runtime) else "shared"))
        flags.append("variant={}".format(str(self.settings.build_type).lower()))
        flags.append("address-model={}".format("32" if self.settings.arch == "x86" else "64"))

        self.run("cd boost_1_64_0 && {} {}".format(("b2" if self.settings.os == "Windows" else "./b2"), " ".join(flags)))

    def package(self):
        self.copy("*.lib", dst="lib", keep_path=False)
        self.copy("*.a", dst="lib", keep_path=False)

        if self.options.shared:
            self.copy("*.dll", dst="bin", keep_path=False)
            self.copy("*.so", dst="lib", keep_path=False)
            self.copy("*.dylib", dst="lib", keep_path=False)

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
