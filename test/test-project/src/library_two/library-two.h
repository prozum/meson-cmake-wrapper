#include "template.h"

#include <string>

namespace two {
class Class {
  public:
    void call(TemplateClass<std::string> arg);
};
}

