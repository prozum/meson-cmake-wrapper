#include "library-two.h"

#include "library-one.h"

#include <iostream>

namespace two {
void Class::call(TemplateClass<std::string> arg) {
    std::cout << one::func(arg);
}
}