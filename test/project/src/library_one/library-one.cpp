#include "library-one.h"

#include "template.ipp"

#include <string>

namespace one {
std::string func(TemplateClass<std::string> arg) {
    return template_function<std::string>(arg.var);
}
}