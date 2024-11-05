/******************************
 * Python Generators for Custom Blocks
 ******************************/
// Import a generator.
import {pythonGenerator, Order} from 'blockly/python';
import { sample_ids } from './globals';
// Python Generator: Load Directory
pythonGenerator.forBlock['load_directory'] = function(block, generator) {
    var dir_name = generator.quote_(block.getFieldValue('DIR'));
    // Generate code with or without directory parameter
    var code = (dir_name === "'directory name'")
        ? 'self.parent.io.open_directory()\nself.store_sample_ids()\n'
        : 'self.parent.open_directory(' + dir_name + ')\nself.store_sample_ids()\n';
    return code;
};

// Python Generator: Select Samples
pythonGenerator.forBlock['select_samples'] = function(block, generator) {
    var sample_id = generator.quote_(block.getFieldValue('SAMPLE_IDS'));
    var code = 'self.parent.change_sample(self.parent.sample_ids.index(' + sample_id + '))\n';
    return code;
};

// Python Generator: Sample IDs List
pythonGenerator.forBlock['sample_ids_list_block'] = function(block, generator) {
    const code = JSON.stringify(sample_ids);  // Generates Python list from global sample_ids variable
    return code;
};

// Python Generator: Iterate Through Sample IDs
pythonGenerator.forBlock['iterate_sample_ids'] = function(block, generator) {
    var variable_sample_ids = JSON.stringify(sample_ids);
    var statements_do = generator.statementToCode(block, 'DO');
    var code = 'for sample_id in ' + variable_sample_ids + ':\n' + statements_do;
    return code;
};

pythonGenerator.forBlock['plot'] = function(block, generator) {
    //const plot_type = generator.valueToCode(block, 'plot_type', Order.ATOMIC);
    var code = '';
    // Access the stored plotType from the block
    var plot_type = block.plotType;
    if (plot_type){
        // TODO: Assemble python into the code variable.
        plot_type = generator.quote_(plot_type);  // Ensure it's safely quoted for Python
        code = 'self.parent.update_SV('+plot_type+')';
    }
    else
    {
        code = 'self.parent.update_SV()';
    }
    return code;
};

pythonGenerator.forBlock['styles'] = function(block, generator) {
    var plot_type = block.plotType;  // Retrieve the stored plot type
    var code = '';

    // Check if plot_type is set
    if (plot_type) {
        
        // Retrieve connected blocks' Python code
        var axisAndLabelsCode = generator.valueToCode(block, 'axisAndLabels',Order.ORDER_NONE) || '{}';
        var annotAndScaleCode = generator.valueToCode(block, 'annotAndScale', Order.ORDER_NONE) || '{}';
        var marksAndLinesCode = generator.valueToCode(block, 'marksAndLines', Order.ORDER_NONE) || '{}';
        var coloringCode = generator.valueToCode(block, 'coloring', Order.ORDER_NONE) || '{}';

        // Assemble the style dictionary
        code = `self.parent.parent.styles[${plot_type}] = {
                "Axes": ${axisAndLabelsCode},
                "Text": ${annotAndScaleCode},
                "Markers": ${marksAndLinesCode},
                "Colors": ${coloringCode}
                }\n`;
        plot_type = generator.quote_(plot_type);
        code += `self.parent.parent.styling.set_style_widgets(${plot_type})\n`;

    }

    return code;
};
pythonGenerator.forBlock['axisAndLabels'] = function(block, generator) {
    const xLabel = generator.quote_(block.getFieldValue('xLabel'));
    const xLimMin = block.getFieldValue('xLimMin');
    const xLimMax = block.getFieldValue('xLimMax');
    const xScale = generator.quote_(block.getFieldValue('xScaleDropdown'));
    const yLabel = generator.quote_(block.getFieldValue('yLabel'));
    const yLimMin = block.getFieldValue('yLimMin');
    const yLimMax = block.getFieldValue('yLimMax');
    const yScale = generator.quote_(block.getFieldValue('yScaleDropdown'));
    const zLabel = generator.quote_(block.getFieldValue('zLabel'));
    const tickDirection = generator.quote_(block.getFieldValue('tickDirectionDropdown'));

    const code = `
{
    "XLabel": ${xLabel},
    "XLim": [${xLimMin}, ${xLimMax}],
    "XScale": ${xScale},
    "YLabel": ${yLabel},
    "YLim": [${yLimMin}, ${yLimMax}],
    "YScale": ${yScale},
    "ZLabel": ${zLabel},
    "TickDir": ${tickDirection}
}`;
    return [code, Order.ATOMIC];
};

pythonGenerator.forBlock['annotAndScale'] = function(block, generator) {
    const scaleDirection = generator.quote_(block.getFieldValue('scaleDirection'));
    const scaleLocation = generator.quote_(block.getFieldValue('scaleLocation'));
    const scaleLength = block.getFieldValue('scaleLength') || 'None';
    const overlayColor = generator.quote_(block.getFieldValue('overlayColor'));
    const font = generator.quote_(block.getFieldValue('font'));
    const fontSize = block.getFieldValue('fontSize');
    const showMass = block.getFieldValue('showMass') === 'TRUE';

    const code = `
{
    "Direction": ${scaleDirection},
    "Location": ${scaleLocation},
    "Length": ${scaleLength},
    "OverlayColor": ${overlayColor},
    "Font": ${font},
    "FontSize": ${fontSize},
    "ShowMass": ${showMass}
}`;
    return [code,Order.ATOMIC];
};

pythonGenerator.forBlock['marksAndLines'] = function(block, generator) {
    const symbol = generator.quote_(block.getFieldValue('symbol'));
    const size = block.getFieldValue('size');
    const transparency = block.getFieldValue('transparency');
    const lineWidth = generator.quote_(block.getFieldValue('lineWidth'));
    const lineColor = generator.quote_(block.getFieldValue('lineColor'));
    const lengthMultiplier = block.getFieldValue('lengthMultiplier');

    const code = `
{
    "Symbol": ${symbol},
    "Size": ${size},
    "Alpha": ${transparency},
    "LineWidth": ${lineWidth},
    "Color": ${lineColor},
    "Multiplier": ${lengthMultiplier}
}`;
    return [code, Order.ATOMIC];
};

pythonGenerator.forBlock['coloring'] = function(block, generator) {
    const colorByField = generator.quote_(block.getFieldValue('colorByField'));
    const field = generator.quote_(block.getFieldValue('field'));
    const resolution = block.getFieldValue('resolution');
    const colormap = generator.quote_(block.getFieldValue('colormap'));
    const reverse = block.getFieldValue('reverse') === 'TRUE';
    const scale = generator.quote_(block.getFieldValue('scale'));
    const cLimMin = block.getFieldValue('cLimMin');
    const cLimMax = block.getFieldValue('cLimMax');
    const cBarLabel = generator.quote_(block.getFieldValue('cBarLabel'));
    const cBarDirection = generator.quote_(block.getFieldValue('cBarDirection'));

    const code = `
{
    "ColorByField": ${colorByField},
    "Field": ${field},
    "Resolution": ${resolution},
    "Colormap": ${colormap},
    "Reverse": ${reverse},
    "Scale": ${scale},
    "CLim": [${cLimMin}, ${cLimMax}],
    "CBarLabel": ${cBarLabel},
    "CBarDirection": ${cBarDirection}
}`;
    return [code, Order.ATOMIC];
};

