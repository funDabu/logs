from typing import Dict

class IJSONSerialize():
    """
    To be implemented:
        - IJSONSerialize._get_attr
        - IJSONSerialize._set_attr
    """
    def __init__(self):
        raise NotImplementedError
    
    def _get_attr(self, name: str):
        """Get a named attribute from an object tranformed
        to a structure that can be encoded to json using json.dumps"""
        raise NotImplementedError
    
    def _set_attr(self, name: str, value):
        """Sets the named attribute on the given object to the specified jvalue.

        The jvalue is a decoded json value for the attribute,
        this method transforms this values to the proper data structure
        and then sets the named attribute.
        
        It works as inversion of _get_attr method
        
        Attributes
        ----------
        name: str
            name of the attribute for given object
        js_value
            decoded json value (using json.load)"""
        raise NotImplementedError

    def json(self) -> Dict:
        """Return representaion of given object that can be serialized to json
        using json.dumps"""
        return {slot : self._get_attr(slot) for slot in self.__slots__}
    
    def from_json(self, js: Dict):
        """Set attributes of givem object according to js.
        Can be used to set attributes according to
        the object returned by self.json method
        
        Parameters
        ----------
        js: Dict
            representaion of given object that can be serialized to json
            using json.dumps
        """
        for slot in self.__slots__:
            self._set_attr(slot, js[slot])
