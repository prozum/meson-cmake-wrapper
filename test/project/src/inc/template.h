#pragma once

#define MAGIC_NUMBER "42"

template <class T> class TemplateClass
{
  public:
    TemplateClass(T arg);
    T var;
};

template <class T>
T template_function(T arg);

