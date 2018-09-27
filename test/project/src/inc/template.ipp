#pragma once

#include "template.h"

template <class T>
TemplateClass<T>::TemplateClass(T arg) {
    this->var = arg;
}

template <class T>
T template_function(T arg){
    puts("Hello from template!");
    puts(MAGIC_NUMBER);
    return arg;
}
