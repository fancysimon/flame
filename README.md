Flame使用帮助
=============

Flame是c++构建系统.

## 安装
    cd common/builder/flame
    sh install

## 依赖软件

* scons 2.0 or higher
* python 2.6 or higher

## 代码库组织

代码库的根目录需要有FLAME_ROOT文件，表明这是一个flame工程目录。
C++的include路径也要从这个根目录写起，这样能有效的减少头文件重名
造成的问题。代码库的根目录可以按照下面的方式来组织:

    FLAME_ROOT
    common
    thirdparty
    your_project

## 构建描述文件

Flame的构建描述文件是BUILD文件，类似Makefile文件。BUILD文件描述
了构建目标名称，依赖的源代码和直接依赖的库等信息。common/config/BUILD
的内容如下：

    cc_library (
        name = 'config',                # 目标名称
        srcs = [
            'config.cc',                # 依赖的源代码
        ],
        deps = [
            ':config_util',             # 直接依赖的当前目录的库
            '//common/file:file_util',  # 直接依赖的其他目录的库，需要从FLAME_ROOT写起
            '//common/string:string',
            '#pthread',                 # 系统库以#开始
        ]
    )

构建config库的命令如下：

    flame build common/config:config

### Flame支持的构建目标有如下几种：
1. cc_library
2. cc_binary
3. cc_test
4. proto_library
5. extra_export

构建目标支持的属性
1. name: 目标名称，和路径一起成为target的唯一标示
2. srcs: 需要的源代码
3. deps: 依赖的其他target

deps支持的格式如下：
1. "//path/path2:name" 从FLAME_ROOT出发的路径为path/path2目录下的名称为name的target
2. ":name" 当前目录下的名称为name的target,路径可以省略
3. "#name" 名称为name的系统库，以#开始

## 构建命令

Flame支持的构建命令有如下几种：

    flame build     构建目标
    flame test      构建并运行单元测试
    flame run       构建并运行一个目标
    flame clean     清理目标
    flame install   构建并打包

构建命令可以指定构建目标(build,test,clean)

    flame build                         # 构建当前目录
    flame build .                       # 构建当前目录
    flame build ...                     # 构建当前目录及所有的子目录
    flame build common/config           # 构建common/config目录
    flame build common/config:config    # 构建common/config目录下的config库
    flame build :config                 # 构建当前目录下的config库

Flame在构建时只构建指定的目标及其依赖(包括直接依赖和间接依赖)，
这样做的目的是加速构建的速度，而传统的构建工具在构建时都会构建整个代码库。

Flame运行支持的参数

    通用
    -h, --help                      show this help message and exit
    -j JOBS, --jobs JOBS            Number of jobs to run simultaneously.
    -p PROFILE, --profile PROFILE   Build profile: debug or release.
    --generate-scons                Generate scons file.

    test
    --args ARGS                     Command line arguments to be passed run or testtargets.

    run
    --args ARGS                     Command line arguments to be passed run or testtargets.

    install
    --prefix PREFIX                 Install prefix path.

## 配置文件

Flame的配置文件是FLAME_ROOT
支持的参数如下：

    include_paths = ['/usr/local/xxx/include']  # 添加非标准的系统库头文件目录
    lib_paths = ['/usr/local/xxx/lib']          # 添加非标准的系统库的路径

## 测试支持
Flame内建支持使用gtest进行单元测试。config库对应的单元测试BUILD文件如下：

    cc_test (
        name = 'config_test',       # 测试目标名称
        srcs = 'config_test.cc',    # 测试依赖的源文件
        deps = [
            ':config',              # 依赖待测试的库，不需要显示依赖gtest库
        ],
        testdata = [
            'testdata/test.conf',   # 单元测试需要使用到的数据
        ],
    )

运行单元测试

    flame test                              # 构建并运行当前目录的单元测试
    flame test ...                          # 构建并运行当前目录及子目录的单元测试
    flame test common/config:config_test    # 构建并运行 config_test 目标

## 第三方库
Flame对第三方库使用的原则是优先使用源码，因为某些原因不能使用源码的库，
可以将头文件和库文件加入工程。需要指定prebuilt=1来定义一个已经编译好的库,
一个简单的例子如下：

    cc_library(
        name = 'AliWS',
        srcs = [],              # prebuild库不依赖源代码
        deps = [
            '#dl',              # 如果依赖其他库也要写上
            '#pthread',
            '#expat',
            '#z',
        ],
        incs = 'include',           # 将include暴露给外面，可以直接include，只允许在prebuild库或thirdparty中使用
        prebuilt=1                  # 指定库为prebuilt类型
    )

对应的目录结构:

    ├── BUILD                       # BUILD文件
    ├── include
    │   ├── ali_tokenizer.h         # prebuild库的头文件要放在include目录
    │   ├── ali_tokenizer_define.h
    │   ├── eng_define.h
    │   ├── eng_interface.h
    │   ├── jpn_define.h
    │   ├── jpn_interface.h
    │   └── pos_tag_define.h
    └── lib
        ├── libAliWS.a              # prebuild库文件要放在lib目录
        └── libAliWS.so             # 需要同时提供.a 和 .so

## 导出动态库和静态库
如果Flame工程下的库需要提供给外部使用，可以使用导出功能。当库被export_static=1
或export_dynamic=1修饰时，在构建时，会将库本身依赖的源码，直接依赖的库，
间接依赖的库的所有源码都构建到库中（prebuild库和系统库除外）。

    cc_library (
        name = 'config',
        srcs = [
            'config.cc',
        ],
        deps = [
            ':config_util',
            '//common/file:file_util',
            '//common/string:string',
            '#pthread',
        ],
        export_static = 1,              # 导出静态库
        export_dynamic = 1,             # 导出动态库
    )

## ProtoBuffer支持

定义ProtoBuffer文件

    package alinlp;

    message EntityTag {
        message Category {
            optional int32 id = 1;
            optional string name = 2;
            optional double weight = 3;
        }
        optional string tag = 1;
        repeated Category categories = 2;
    }

    message EntityTags {
        repeated EntityTag records = 1;
    }

对应的BUILD文件如下:

    proto_library (
        name = 'entity_tag_proto',          # ProtoBuffer库名称
        srcs = 'entity_tag.proto',
    )

    cc_library (
        name = 'entity_classifier',
        srcs = 'entity_classifier.cc',
        deps = [
            ':entity_tag_proto',            # 依赖ProtoBuffer库
        ],
    )

proto_library会调用protoc生成对应的 .h 和 .cc，并构建出对应的库
c++使用proto_library时，直接依赖proto_library即可。

## 打包支持

Flame支持打包，对应的命令如下：

    flame install                           # 默认打包到release目录
    flame install --prefix=/home/release    # 指定打包路径
    flame install ... --prefix=release      # 构建单签目录和子目录并打包

打包规则
1. 将binary打包到指定目录下的bin目录
2. 将导出静态库，导出动态库打包到指定目录下的lib目录
3. 将extra_export中指定的头文件打包到指定目录下的include目录
4. 将extra_export中指定的数据文件打包到指定目录下的data目录

extra_export使用方式

    extra_export (
        headers = [
            'document.h',
            'intention_classifier.h',
        ],
        files = [
            'data/test.txt',
        ],
    )

