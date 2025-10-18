from abc import ABC, abstractmethod


class Product(ABC):
    @abstractmethod
    def operation(self):
        pass


class ProductOne(Product):
    def operation(self):
        return "From Product One"
    

class ProductTwo(Product):
    def operation(self):
        return "From Product Two"
    

class Creator(ABC):
    @abstractmethod
    def factory_method(self):
        pass

    def perform_operation(self):
        product = self.factory_method()
        result = product.operation()
        return f"Creator: {result}"


class CreatorOne(Creator):
    def factory_method(self):
        return ProductOne()
    

class CreatorTwo(Creator):
    def factory_method(self):
        return ProductTwo()
    

def client_code(creator):
    print(creator.perform_operation())


if __name__ == "__main__":
    client_code(CreatorOne())
    client_code(CreatorTwo())
