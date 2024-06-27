import pandas as pd

class AttributeDataFrame(pd.DataFrame):
    """Creates a dataframe with attributes and them means to get and set them.

    Create a dataframe with column attributes or add attributes to existing columns of a dataframe and methods to get and set them.

    Parameters
    ----------
    pandas.DataFrame : 
        Input dataframe, if none provided an empty dataframe can be created, defaults to None

    Returns
    -------
    AttributeDataFrame
        Adds column attributes and sets their values to a dataframe

    Examples
    --------
    Example 1: Creating the DataFrame with no initial data
    df = AttributeDataFrame()
    print(df)  # Output: Empty DataFrame

    # Adding data and attributes
    df['Temperature'] = [22, 23, 21]
    df.set_attribute('Temperature', 'units', 'Celsius')
    df.set_attribute('Temperature', 'average', 22)
    df.set_attribute('Temperature', 'uncertainty', 1)

    print(df)
    print(df.get_attribute('Temperature', 'units'))         # Output: Celsius
    print(df.get_attribute('Temperature', 'average'))       # Output: 22
    print(df.get_attribute('Temperature', 'uncertainty'))   # Output: 1

    Example 2: Creating the DataFrame from an existing dataframe
    
    #df = AttributeDataFrame(data, column_attributes=column_attributes)

    # Accessing attributes using methods
    #print(df.get_attribute('Temperature', 'units'))         # Output: Celsius
    #print(df.get_attribute('Pressure', 'average'))          # Output: 101

    # Setting new attributes
    #df.set_attribute('Temperature', 'range', (20, 25))
    #print(df.get_attribute('Temperature', 'range'))         # Output: (20, 25)
    """    
    _metadata = ['column_attributes']
    
    @property
    def _constructor(self):
        return AttributeDataFrame
    
    def __init__(self, data=None, *args, **kwargs):
        # Initialize column attributes
        self.column_attributes = kwargs.pop('column_attributes', {})
        
        # If no data is provided, initialize with an empty DataFrame
        if data is None:
            data = {}
        
        # Initialize the DataFrame
        super(AttributeDataFrame, self).__init__(data, *args, **kwargs)
    
    def get_attribute(self, column, attribute):
        """Get an attribute from an AttributeDataFrame

        Get the values of an attribute.

        Parameters
        ----------
        column : str
            Name of column
        attribute : str
            Name of attribute

        Returns
        -------
        any
            Attribute value

        Examples
        --------
        df = AttributeDataFrame()
        df['Temperature'] = [22, 23, 21]
        df.set_attribute('Temperature', 'units', 'Celsius')
        print(df.get_attribute('Temperature', 'units'))
        """        
        return self.column_attributes.get(column, {}).get(attribute)

    def set_attribute(self, column, attribute, value):
        """Set attribute of an AttributeDataFrame

        Adds an attribute to a dataframe

        Parameters
        ----------
        column : str
            Name of AttributeDataFrame column
        attribute : str
            Name of attribute
        value : any
            Value associated with attribute

        Examples
        --------
        # Creating the DataFrame with no initial data
        df = AttributeDataFrame()

        # Adding data and attributes
        df['Temperature'] = [22, 23, 21]
        df.set_attribute('Temperature', 'units', 'Celsius')
        """        
        if column not in self.column_attributes:
            self.column_attributes[column] = {}
        self.column_attributes[column][attribute] = value