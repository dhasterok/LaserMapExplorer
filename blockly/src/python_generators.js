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
    // Retrieve the stored plotType from the block
    var plot_type = block.plotType ? generator.quote_(block.plotType) : 'None';

    // Initialize an empty code string
    var code = '';

    // Check if a `style` block is connected
    var styleCode = generator.valueToCode(block, 'style', Order.NONE);
    if (styleCode && styleCode !== '{}') {
        code += `
self.parent.style.style_dict[${plot_type}] = {**self.parent.style.style_dict[${plot_type}], **${styleCode}}
self.parent.style.set_style_widgets(${plot_type})
`;
    }

    // Update the visualization regardless of the style connection
    code += `self.parent.update_SV(${plot_type})\n`;
    return code;
};


pythonGenerator.forBlock['styles'] = function(block, generator) {
    // Retrieve code for each connected sub-block, default to an empty object if not connected
    var axisAndLabelsCode = generator.valueToCode(block, 'axisAndLabels', Order.NONE);
    var annotAndScaleCode = generator.valueToCode(block, 'annotAndScale', Order.NONE);
    var marksAndLinesCode = generator.valueToCode(block, 'markersAndLines', Order.NONE);
    var coloringCode = generator.valueToCode(block, 'coloring', Order.NONE);

    // Construct the style dictionary with only non-empty entries
    var styleDict = [];
    if (axisAndLabelsCode && axisAndLabelsCode !== '{}') styleDict.push(`"Axes": ${axisAndLabelsCode}`);
    if (annotAndScaleCode && annotAndScaleCode !== '{}') styleDict.push(`"Text": ${annotAndScaleCode}`);
    if (marksAndLinesCode && marksAndLinesCode !== '{}') styleDict.push(`"Markers": ${marksAndLinesCode}`);
    if (coloringCode && coloringCode !== '{}') styleDict.push(`"Colors": ${coloringCode}`);

    // Assemble the dictionary as a string, ensuring only non-empty values are included
    var code = `{${styleDict.join(', ')}}`;
    
    return [code, Order.ATOMIC];
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

