#!/usr/bin/env python3
"""
Generate enums.hpp and enums.cpp for libsigrokcxx directly from libsigrok.h.

enums.hpp must be included from libsigrokcxx.hpp AFTER the EnumValue template
is defined (matches upstream Makefile dependency ordering).
"""

import os
import re
import sys

MAPPING = [
    ('sr_loglevel', ('LogLevel', 'Log verbosity level')),
    ('sr_packettype', ('PacketType', 'Type of datafeed packet')),
    ('sr_mq', ('Quantity', 'Measured quantity')),
    ('sr_unit', ('Unit', 'Unit of measurement')),
    ('sr_mqflag', ('QuantityFlag', 'Flag applied to measured quantity')),
    ('sr_configkey', ('ConfigKey', 'Configuration key')),
    ('sr_configcap', ('Capability', 'Configuration capability')),
    ('sr_datatype', ('DataType', 'Configuration data type')),
    ('sr_channeltype', ('ChannelType', 'Channel type')),
    ('sr_trigger_matches', ('TriggerMatchType', 'Trigger match type')),
    ('sr_output_flag', ('OutputFlag', 'Flag applied to output modules')),
]

ENUMS_WITH_METHODS = {'ConfigKey', 'QuantityFlag'}


def parse_enums(header_path):
    with open(header_path, 'r', encoding='utf-8') as f:
        content = f.read()
    enums = {}
    for enum_name, (cls_name, brief) in MAPPING:
        pattern = r'enum\s+' + re.escape(enum_name) + r'\s*\{(.*?)\};'
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            print(f"WARNING: could not find enum {enum_name}", file=sys.stderr)
            continue
        body = match.group(1)
        members = []
        for line in body.split('\n'):
            line = line.strip()
            if not line or line.startswith('/*') or line.startswith('*') or line.startswith('*/'):
                continue
            if line.startswith('//'):
                continue
            if line.endswith(','):
                line = line[:-1].strip()
            if not line:
                continue
            m = re.match(r'(\w+)\s*(?:=\s*(.+))?', line)
            if m:
                members.append((m.group(1), m.group(2)))
        enums[enum_name] = (cls_name, brief, members)
    return enums


def generate_header(enums, output_dir):
    """Generate enums.hpp - must be included from libsigrokcxx.hpp (after EnumValue defined)."""
    header_path = os.path.join(output_dir, 'include', 'libsigrokcxx', 'enums.hpp')
    os.makedirs(os.path.dirname(header_path), exist_ok=True)
    with open(header_path, 'w') as f:
        print("/* Generated file - edit gen_enums.py instead! */", file=f)
        print("#ifndef LIBSIGROKCXX_GENERATED_ENUMS_HPP", file=f)
        print("#define LIBSIGROKCXX_GENERATED_ENUMS_HPP", file=f)
        print(file=f)
        print("// Included from libsigrokcxx.hpp after EnumValue is defined.", file=f)
        print("namespace sigrok {", file=f)
        print(file=f)
        for enum_name, (cls_name, brief, members) in enums.items():
            trimmed_names = [re.sub(r'^SR_[A-Z]+_', '', n) for n, v in members]
            print(f"template<> const SR_API std::map<const enum {enum_name}, const {cls_name} * const> sigrok::EnumValue<{cls_name}, enum {enum_name}>::_values;", file=f)
            print(file=f)
            print(f"/** {brief} */", file=f)
            print(f"class SR_API {cls_name} : public EnumValue<{cls_name}, enum {enum_name}>", file=f)
            print("{", file=f)
            print("public:", file=f)
            for trimmed in trimmed_names:
                print(f"    static const {cls_name} * const {trimmed};", file=f)
            methods_file = os.path.join(output_dir, '..', 'bindings', 'cxx', f'{cls_name}_methods.hpp')
            if cls_name in ENUMS_WITH_METHODS and os.path.exists(methods_file):
                with open(methods_file, 'r') as mf:
                    print(mf.read(), file=f)
            print(file=f)
            print("protected:", file=f)
            print(f"    {cls_name}(enum {enum_name} id, const char name[]) : EnumValue(id, name) {{}}", file=f)
            print(file=f)
            for trimmed in trimmed_names:
                print(f"    static const {cls_name} _{trimmed};", file=f)
            print("};", file=f)
            print(file=f)
        print("} // namespace sigrok", file=f)
        print(file=f)
        print("#endif /* LIBSIGROKCXX_GENERATED_ENUMS_HPP */", file=f)
    return header_path


def generate_source(enums, output_dir):
    """Generate enums.cpp - included from classes.cpp at compile time.
    
    classes.cpp includes this file, so all types from libsigrokcxx.hpp
    are already available. No using directive needed.
    """
    source_path = os.path.join(output_dir, 'enums.cpp')
    with open(source_path, 'w') as f:
        print("/* Generated file - edit gen_enums.py instead! */", file=f)
        print("// Included via #include <enums.cpp> in classes.cpp", file=f)
        print("// All types from libsigrokcxx.hpp are available", file=f)
        print(file=f)
        for enum_name, (cls_name, brief, members) in enums.items():
            member_names = [m[0] for m in members]
            trimmed_names = [re.sub(r'^SR_[A-Z]+_', '', n) for n in member_names]
            for name, trimmed in zip(member_names, trimmed_names):
                print(f"const sigrok::{cls_name} sigrok::{cls_name}::_{trimmed} = sigrok::{cls_name}({name}, \"{trimmed}\");", file=f)
            print(file=f)
            for trimmed in trimmed_names:
                print(f"const sigrok::{cls_name} * const sigrok::{cls_name}::{trimmed} = &sigrok::{cls_name}::_{trimmed};", file=f)
            print(file=f)
            print(f"template<> const SR_API std::map<const enum {enum_name}, const sigrok::{cls_name} * const> sigrok::EnumValue<sigrok::{cls_name}, enum {enum_name}>::_values = {{", file=f)
            for name, trimmed in zip(member_names, trimmed_names):
                print(f"    {{{name}, sigrok::{cls_name}::{trimmed}}},", file=f)
            print("};", file=f)
            print(file=f)
            methods_file = os.path.join(output_dir, '..', 'bindings', 'cxx', f'{cls_name}_methods.cpp')
            if cls_name in ENUMS_WITH_METHODS and os.path.exists(methods_file):
                with open(methods_file, 'r') as mf:
                    print(mf.read(), file=f)
    return source_path


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <libsigrok.h> <output_dir>", file=sys.stderr)
        sys.exit(1)
    header_path = sys.argv[1]
    output_dir = sys.argv[2]
    enums = parse_enums(header_path)
    if not enums:
        print("ERROR: No enums parsed!", file=sys.stderr)
        sys.exit(1)
    header_file = generate_header(enums, output_dir)
    source_file = generate_source(enums, output_dir)
    print(f"Generated {header_file}")
    print(f"Generated {source_file}")
    print(f"Total enums: {len(enums)}")


if __name__ == '__main__':
    main()
