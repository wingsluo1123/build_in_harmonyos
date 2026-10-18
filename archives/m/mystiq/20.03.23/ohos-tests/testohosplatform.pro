CONFIG += qtestlib
TEMPLATE = app
TARGET = testohosplatform

QT += core gui widgets testlib

HEADERS += \
    testohosplatform.h \
    ../../services/notification.h \
    ../../services/notificationservice.h \
    ../../converter/exepath.h

SOURCES += \
    testohosplatform.cpp \
    ../../services/notification.cpp \
    ../../services/notificationservice.cpp \
    ../../services/notificationservice-qt.cpp \
    ../../services/notificationservice-notifysend.cpp \
    ../../converter/exepath.cpp
