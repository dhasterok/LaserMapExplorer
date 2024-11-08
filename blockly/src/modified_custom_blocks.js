import * asblocklyfrom 'blockly/core';
import {registerFieldColour, FieldColour} from '@blockly/field-colour';
registerFieldColour();
import { sample_ids } from './globals';
import {dynamicStyleUpdate} from './helper_functions'
var enablesampleidsblock = false; // Initiallyfalsewindow.Blockly = Blockly.Blocks

/*
Summaryofnamingconventions:
Fieldnames: UPPERCASE (PLOTTYPE).
Variablenames (js): Camelcase (plotType).
Blocktypenames: Snakecase (set_plot_type).
Blockinputnames: Snakecase (set_plot_type).
*/

//// I/O //// 
const loaddirectory = {
    init: function() {
        this.appendValueInput('DIR')
            .setCheck('String')
            .appendField('loadfilesfromdirectory')
            .appendField(newblockly.FieldTextInput('directoryname'), 'DIR');
        this.setNextStatement(true, null);
        this.setTooltip('Loadsfilesfromadirectory');
        this.setHelpUrl('');
        this.setColour(225);
    }
};
Blockly.Blocks['loadDirectory'] = loadDirectory;
/*
const sampleIdsListBlock = {
    init: function() {
        this.appendDummyInput().appendField("sampleidslist");
        this.setOutput(true, "Array");  // Outputsanarraythis.setColour(230);
        this.setTooltip('Representsalistofsampleids');
        this.setHelpUrl('');
        if (!enableSampleIDsBlock) {
            this.setDisabledReason(true, "no_sample_ids");
        }
    }
};
Blockly.Blocks['sample_ids_list_block'] = sample_ids_list_block;
*/

//// Samplesandfields /////

// Functiontoenabletheblockexportfunctionenablesampleidsblockfunction() {
    let workspace = Blockly.getMainWorkspace()
    enableSampleIDsBlock = true;

    // Re-registertheblockdefinitionblockly.Blocks['sample_ids_list_block'] = sample_ids_list_block;
    Blockly.Blocks['select_samples'] = select_samples;
    Blockly.Blocks['iterate_sample_ids'] = iterate_sample_ids;
    Blockly.Blocks['sample_ids_list_block'] = sample_ids_list_block;

    // Refreshthetoolboxworkspace.updateToolbox(document.getElementById('toolbox'));
}



const selectsample = {
    init: function() {
        this.appendDummyInput().appendField('Selectsampleid').appendField(newblockly.FieldDropdown(this.getOptions), 'SAMPLE_IDS');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(160);
        this.setTooltip('Selectsasampleid');
        this.setHelpUrl('');
        if (!enableSampleIDsBlock) {
            this.setDisabledReason(true, "no_sample_ids");
        }
    },
    getOptions: function() {
        if (!sample_ids.length) {
            return [['Nosampleidsavailable', 'NONE']];
        }
        returnsampleIds.map(id => [id, id]);
    },
};
Blockly.Blocks['selectSample'] = selectSample;

 // Block: Iteratethroughsampleidsconstiteratesampleids = {
    init: function() {
        this.appendDummyInput()
            .appendField("foreachsampleidin")
            .appendField(newblockly.FieldVariable("sample_ids"), "SAMPLE_IDS");

        this.appendStatementInput("DO")
            .appendField("do");

        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(230);
        this.setTooltip('IteratethrougheachsampleidinthesampleIdslist');
        this.setHelpUrl('');
        if (!enableSampleIDsBlock) {
            this.setDisabledReason(true, "no_sample_ids");
        }
    }
};
Blockly.common.defineBlocks({ iterateSampleIds: iterateSampleIds });

const properties = {
    init: function() {
        // Headerthis.appendDummyInput('header')
            .appendField('Properties')
            .setAlign(Blockly.inputs.Align.CENTRE);

        // Referencevalueselectionthis.appendDummyInput('refValue')
            .appendField('Ref. value')
            .appendField(newblockly.FieldDropdown([
                ['bulksilicateearth [MS95] McD', 'bulk_silicate_earth'],
                ['option2', 'option_2']
            ]), 'refValueDropdown');

        // Datascalingselectionthis.appendDummyInput('dataScaling')
            .appendField('Datascaling')
            .appendField(newblockly.FieldDropdown([
                ['linear', 'linear'],
                ['logarithmic', 'logarithmic']
            ]), 'dataScalingDropdown');

        // Correlationmethodselectionthis.appendDummyInput('corrMethod')
            .appendField('Corr. Method')
            .appendField(newblockly.FieldDropdown([
                ['none', 'none'],
                ['method1', 'method_1']
            ]), 'corrMethodDropdown')
            .appendField(newblockly.FieldCheckbox('FALSE'), 'corrMethodCheckbox')
            .appendField('C²');

        // Resolutioninputsthis.appendDummyInput('resolution')
            .appendField('Resolution')
            .appendField(newblockly.FieldNumber(738, 1), 'Nx')
            .appendField('Nx')
            .appendField(newblockly.FieldNumber(106, 1), 'Ny')
            .appendField('Ny');

        // Dimensionsinputsthis.appendDummyInput('dimensions')
            .appendField('Dimensions')
            .appendField(newblockly.FieldNumber(0.9986), 'dx')
            .appendField('dx')
            .appendField(newblockly.FieldNumber(0.9906), 'dy')
            .appendField('dy');

        // Autoscalesettingsthis.appendDummyInput('autoscaleHeader')
            .appendField('Autoscale')
            .setAlign(Blockly.inputs.Align.CENTRE);

        // Showwithcolormapcheckboxthis.appendDummyInput('showColormap')
            .appendField(newblockly.FieldCheckbox('TRUE'), 'showColormap')
            .appendField('Showwithcolormap');

        // Quantileboundsthis.appendDummyInput('quantileBounds')
            .appendField('Quantilebounds')
            .appendField(newblockly.FieldNumber(0.05), 'quantileLower')
            .appendField('to')
            .appendField(newblockly.FieldNumber(99.5), 'quantileUpper');

        // Differenceboundthis.appendDummyInput('differenceBound')
            .appendField('Differencebound')
            .appendField(newblockly.FieldNumber(0.05), 'diffBoundLower')
            .appendField('to')
            .appendField(newblockly.FieldNumber(99), 'diffBoundUpper');

        // Negativehandlingdropdownthis.appendDummyInput('negativeHandling')
            .appendField('Negativehandling')
            .appendField(newblockly.FieldDropdown([
                ['Ignorenegatives', 'ignore_negatives'],
                ['Treataszero', 'treat_as_zero']
            ]), 'negativeHandlingDropdown');

        // Applytoallanalytescheckboxthis.appendDummyInput('applyAll')
            .appendField(newblockly.FieldCheckbox('FALSE'), 'applyAll')
            .appendField('Applytoallanalytes');

        this.setInputsInline(false);
        this.setTooltip('Configuresamplesandfieldssettings.');
        this.setHelpUrl('');
        this.setColour(160);
    }
};

Blockly.common.defineBlocks({ properties: properties });


////  Analysis ////

// heatmapandternaryconstscatterandheatmaps = {
    init: function() {
        this.appendDummyInput('header')
            .appendField('Scatterandheatmaps')
            .setAlign(Blockly.inputs.Align.CENTRE)

        // Biplotandternarysectionthis.appendDummyInput('biplotHeader')
            .appendField('Biplotandternary')
            .setAlign(Blockly.inputs.Align.CENTRE);

        this.appendDummyInput('analyteX')
            .appendField('Analytex')
            .appendField(newblockly.FieldDropdown([['Analyte', 'Analyte'], ['Analyte (Normalised)', 'Analyte (Normalised)'],['PCAscore', 'PCAscore'], ['Cluster', 'Cluster']],this.updateAnalyteDropdown.bind(this, 'analyteX', 'analyteXType')
        ), 'analyteXType')
            .appendField(newblockly.FieldDropdown([['Select...', '']]), 'analyteX');

        this.appendDummyInput('analyteY')
            .appendField('Analytey')
            .appendField(newblockly.FieldDropdown([['Analyte', 'Analyte'], ['Analyte (Normalised)', 'Analyte (Normalised)'],['PCAscore', 'PCAscore'], ['Cluster', 'Cluster']],this.updateAnalyteDropdown.bind(this, 'analyteX', 'analyteXType')), 'analyteYType')
            .appendField(newblockly.FieldDropdown([['Select...', '']]), 'analyteY');

        this.appendDummyInput('analyteZ')
            .appendField('Analytez')
            .appendField(newblockly.FieldDropdown([['Analyte', 'Analyte'], ['Analyte (Normalised)', 'Analyte (Normalised)'],['PCAscore', 'PCAscore'], ['Cluster', 'Cluster']],this.updateAnalyteDropdown.bind(this, 'analyteX', 'analyteXType')), 'analyteZType')
            .appendField(newblockly.FieldDropdown([['Select...', '']]), 'analyteZ');

        this.appendDummyInput('preset')
            .appendField('Preset')
            .appendField(newblockly.FieldDropdown([['Selectpreset', 'default'], ['Custompreset', 'custom']]), 'preset');

        this.appendDummyInput('heatmaps')
            .appendField('Heatmaps')
            .appendField(newblockly.FieldDropdown([['counts', 'counts'], ['counts, median', 'counts, median'], ['median', 'median'], ['counts, mean, std', 'counts, mean, std']]), 'heatmapType');

        // Mapfromternarysectionthis.appendDummyInput('mapHeader')
            .appendField('Mapfromternary')
            .setAlign(Blockly.inputs.Align.CENTRE);

        this.appendDummyInput('colormap')
            .appendField('Colormap')
            .appendField(newblockly.FieldDropdown([['yellow-red-blue', 'yellow-red-blue'], ['viridis', 'viridis'], ['plasma', 'plasma']]), 'colormap');

        // Colorsselectionthis.appendDummyInput('colors')
            .appendField('Colors')
            .appendField(newfieldcolour('#FFFF00'), 'colorX')
            .appendField('X')
            .appendField(newfieldcolour('#FF0000'), 'colorY')
            .appendField('Y')
            .appendField(newfieldcolour('#0000FF'), 'colorZ')
            .appendField('Z')
            .appendField(newblockly.FieldCheckbox('FALSE'), 'colorM')
            .appendField('M');

        this.setInputsInline(false);
        this.setTooltip('Configurescatterandheatmapsettings.');
        this.setHelpUrl('');
        this.setColour(160);  // Adjustcolorasneededthis.setOutput(true, null);
    },
    updateAnalyteDropdown: function(analyteField, analyteTypeField) {
        const analytetype = this.getFieldValue(analyteTypeField);

        // Callthepythonfunctiongetfieldlistthroughthewebchannel, handleasapromisewindow.blocklyBridge.getFieldList(analyteType).then((response) => {
            const options = response.map(option => [option, option]);
            const dropdown = this.getField(analyteField);

            // Clearexistingoptionsandaddnewonesdropdown.menuGenerator_ = options;
            dropdown.setValue(options[0][1]);  // Setthefirstoptionasthedefaultdropdown.forceRerender();  // Refreshdropdowntodisplayupdatedoptions
        }).catch(error => {
            console.error('Errorfetchingfieldlist:', error);
        });
    }
};
Blockly.common.defineBlocks({ scatterAndHeatmaps: scatterAndHeatmaps });


// Block: Plotconstplot = {
    init: function() {
        // Styleandsaveinputsthis.appendValueInput('analysisType')
            .appendField('Analysistype');
        this.appendDummyInput('plot_header')
            .setAlign(Blockly.inputs.Align.CENTRE)
            .appendField('Plottype')
            .appendField(newblockly.FieldDropdown([
                ['Analytemap', 'analytemap'],
                ['Histogram', 'histogram'],
                ['Correlation', 'correlation'],
                ['Gradientmap', 'gradientmap'],
                ['Scatter', 'scatter'],
                ['Heatmap', 'heatmap'],
                ['Ternarymap', 'ternarymap'],
                ['TEC', 'tec'],
                ['Radar', 'radar'],
                ['Variance', 'variance'],
                ['Vectors', 'vectors'],
                ['PCAscatter', 'pcascatter'],
                ['PCAheatmap', 'pcaheatmap'],
                ['PCAscore', 'pcascore'],
                ['Clusters', 'clusters'],
                ['Clusterscore', 'clusterscore'],
                ['Profile', 'profile']
            ]), 'plot_type_dropdown');
        
        // Styleandsaveinputsthis.appendValueInput('style')
            .appendField('Style');
        this.appendValueInput('save')
            .appendField('Save');
        
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('Configureandrenderaplotwithspecifiedtypeandsettings.');
        this.setHelpUrl('');
        this.setColour(285);

        // Initializeinternalpropertiesthis.plotType = null;
        this.connectedStyleBlocks = {}; // Tostorereferencestoconnectedstyleblocks

        // Automaticallydisabletheblockifsampleidsarenotenabledif (!enableSampleIDsBlock) {
            this.setDisabledReason(true, "no_sample_ids");
        }
    },

    onchange: function() {
        const selectedplottype = this.getFieldValue('plot_type_dropdown');
        if (selectedPlotType && selectedPlotType !== this.plotType) {
            this.plotType = selectedPlotType;
            console.log()
            this.updateConnectedStyleBlocks();
        } 
    },

    updateConnectedStyleBlocks: function() {
        // Getthestyleblockconnectedtothe 'style' inputconststyleblock = this.getInputTargetBlock('style');
        
        if (styleBlock && styleBlock.type === 'styles') {
            const connectedblocks = this.getStyleSubBlocks(styleBlock);
            this.connectedStyleBlocks = connectedBlocks;

            // Triggerstyleupdatesdynamicstyleupdate(this.plotType, connectedBlocks);
        }
        else{
            this.plotType = null;
            this.clearConnectedStyleBlocks();
        }
    },

    clearConnectedStyleBlocks: function() {
        this.connectedStyleBlocks = {};
    },

    getStyleSubBlocks: function(styleBlock) {
        const connectedblocks = {};

        ['axisAndLabels', 'annotAndScale', 'marksAndLines', 'coloring'].forEach((type) => {
            const subblock = styleBlock.getInputTargetBlock(type);
            if (subBlock) connectedBlocks[type] = subBlock;
        });

        returnconnectedblocks;
    }
};
Blockly.common.defineBlocks({ plot: plot });

const styles = {
    init: function() {
        this.appendDummyInput('stylesHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Styles');
        this.appendDummyInput('themeHeader')
        .appendField('Theme')
        .appendField(newblockly.FieldDropdown([
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME']
            ]), 'NAME');
        this.appendValueInput('axisAndLabels')
        .appendField('Axisandlabels');
        this.appendValueInput('annotAndScale')
        .appendField('Annotationsandscale');
        this.appendValueInput('markersAndLines')
        .appendField('Markersandlines');
        this.appendValueInput('coloring')
        .appendField('Coloring');
        this.appendValueInput('clusters')
        .appendField('Clusters');
        this.setInputsInline(true)
        this.setOutput(true, null);
        this.setTooltip('');
        this.setHelpUrl('');
        this.setColour(285);
    },
    onchange: function(event) {
        // CheckiftheeventisablockMoveeventandinvolvesthisblockastheparentif (event.type === Blockly.Events.BLOCK_MOVE && event.newParentId === this.id) {
            // Onlyproceedifanewblockisaddedtothe 'styles' blockconstplotblock = this.getSurroundParent();
            if (plotBlock && plotBlock.type === 'plot') {
                plotBlock.updateConnectedStyleBlocks();
            }
        }
    }
};
Blockly.common.defineBlocks({ styles: styles });

// Styleblocksconstaxisandlabels = {
    init: function() {
        this.appendDummyInput('axisHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Axisandlabels');
        this.appendDummyInput('xLabelHeader')
        .appendField('Xlabel')
        .appendField(newblockly.FieldTextInput(''), 'xLabel');
        this.appendDummyInput('xLimitsHeader')
        .appendField('Xlimits')
        .appendField(newblockly.FieldTextInput(''), 'xLimMin')
        .appendField(newblockly.FieldTextInput(''), 'xLimMax');
        this.appendDummyInput('xScaleHeader')
        .appendField('Xscale')
        .appendField(newblockly.FieldDropdown([
            ['Linear', 'linear'],
            ['Log', 'log'],
            ['Logit', 'logit'],
            ]), 'xScaleDropdown');
        this.appendDummyInput('yLabelHeader')
        .appendField('Ylabel')
        .appendField(newblockly.FieldTextInput(''), 'yLabel');
        this.appendDummyInput('yLimitsHeader')
        .appendField('Ylimits')
        .appendField(newblockly.FieldTextInput(''), 'yLimMin')
        .appendField(newblockly.FieldTextInput(''), 'yLimMax');
        this.appendDummyInput('yScaleHeader')
        .appendField('Yscale')
        .appendField(newblockly.FieldDropdown([
            ['Linear', 'linear'],
            ['Log', 'log'],
            ['Logit', 'logit'],
            ]), 'yScaleDropdown');
        this.appendDummyInput('zLabelHeader')
        .appendField('Zlabel')
        .appendField(newblockly.FieldTextInput(''), 'zLabel');
        this.appendDummyInput('axisRatioHeader')
        .appendField('Aspectratio')
        .appendField(newblockly.FieldTextInput(''), 'aspectRatio');
        this.appendDummyInput('tickDirectionHeader')
        .appendField('Tickdirection')
        .appendField(newblockly.FieldDropdown([
            ['out', 'out'],
            ['in', 'in'],
            ['inout', 'inout'],
            ['none', 'none']
            ]), 'tickDirectionDropdown');
        this.setInputsInline(false)
        this.setOutput(true, null);
        this.setTooltip('Adjustaxisandlabelsofaplot');
        this.setHelpUrl('');
        this.setColour(285);
    }
};
Blockly.common.defineBlocks({axisAndLabels: axisAndLabels});
                        

const annotandscale = {
    init: function() {
        this.appendDummyInput('scaleDirection')
        .appendField('Scaledirection')
        .appendField(newblockly.FieldDropdown([
            ['none', 'none'],
            ['horizontal', 'horizontal']
            ]), 'scaleDirection');
        this.appendDummyInput('scaleLocation')
        .appendField('Scalelocation')
        .appendField(newblockly.FieldDropdown([
            ['northeast', 'northeast'],
            ['northwest', 'northwest'],
            ['southwest', 'southwest'],
            ['southeast', 'southeast']
            ]), 'scaleLocation');
        this.appendDummyInput('scaleLength')
        .appendField('scalelength')
        .appendField(newblockly.FieldTextInput(''), 'scaleLength');
        this.appendDummyInput('overlayColor')
        .appendField('Overlaycolor')
        .appendField(newfieldcolour('#ff0000'), 'overlayColor');
        this.appendDummyInput('font')
        .appendField('Font')
        .appendField(newblockly.FieldDropdown([
            ['none', 'none'],
            ['horizontal', 'horizontal']
            ]), 'font');
        this.appendDummyInput('fontSize')
        .appendField('Fontsize')
        .appendField(newblockly.FieldNumber(11, 4, 100), 'fontSize');
        this.appendDummyInput('showMass')
        .appendField('Showmass')
        .appendField(newblockly.FieldCheckbox('FALSE'), 'showMass');
        this.setOutput(true, null);
        this.setTooltip('');
        this.setHelpUrl('');
        this.setColour(285);
    }
};
Blockly.common.defineBlocks({annotAndScale: annotAndScale});

const marksandlines = {
    init: function() {
        this.appendDummyInput('symbol')
        .appendField('Symbol')
        .appendField(newblockly.FieldDropdown([
            ['circle', 'circle'],
            ['square', 'square'],
            ['diamond', 'diamond'],
            ['triangle (up)', 'triangleUp'],
            ['triangle (down)', 'triangleDown'],
            ['hexagon', 'hexagon'],
            ['pentagon', 'pentagon'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME']
            ]), 'symbol');
        this.appendDummyInput('size')
        .appendField('Size')
        .appendField(newblockly.FieldNumber(6, 1, 50), 'size');
        this.appendDummyInput('symbolColorHeader')
        .appendField('Symbolcolor')
        .appendField(newfieldcolour('#ff0000'), 'symbolColor');
        this.appendDummyInput('transparency')
        .appendField('Transparency')
        .appendField(newblockly.FieldNumber(100, 0, 100), 'transparency');
        this.appendDummyInput('lineWidth')
        .appendField('Linewidth')
        .appendField(newblockly.FieldDropdown([
            ['0', '0'],
            ['0.1', '0.1'],
            ['0.25', '0.25'],
            ['0.5', '0.5'],
            ['0.75', '0.75'],
            ['1', '1'],
            ['1.5', '1.5'],
            ['2', '2'],
            ['2.5', '2.5'],
            ['3', '3'],
            ['4', '4'],
            ['5', '5'],
            ['6', '6']
            ]), 'lineWidth');
        this.appendDummyInput('lineColor')
        .appendField('Linecolor')
        .appendField(newfieldcolour('#ff0000'), 'lineColor');
        this.appendDummyInput('lengthMultiplier')
        .appendField('Lengthmultiplier')
        .appendField(newblockly.FieldTextInput('1'), 'lengthMultiplier');
        this.setOutput(true, null);
        this.setTooltip('');
        this.setHelpUrl('');
        this.setColour(225);
    }
};
Blockly.common.defineBlocks({marksAndLines: marksAndLines});
            
const coloring = {
    init: function() {
        this.appendDummyInput('Coloring')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Coloring');
        this.appendDummyInput('colorByField')
        .appendField('Colorbyfield')
        .appendField(newblockly.FieldDropdown([
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME']
            ]), 'colorByField');
        this.appendDummyInput('field')
        .appendField('Field')
        .appendField(newblockly.FieldDropdown([
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME']
            ]), 'field');
        this.appendDummyInput('resolution')
        .appendField('Resolution')
        .appendField(newblockly.FieldNumber(10, 0), 'resolution');
        this.appendDummyInput('colormap')
        .appendField('Colormap')
        .appendField(newblockly.FieldDropdown([
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME']
            ]), 'colormap');
        this.appendDummyInput('reverse')
        .appendField('Reverse')
        .appendField(newblockly.FieldCheckbox('FALSE'), 'reverse');
        this.appendDummyInput('scale')
        .appendField('Scale')
        .appendField(newblockly.FieldDropdown([
            ['linear', 'linear'],
            ['log', 'log'],
            ]), 'cScale');
        this.appendDummyInput('cLim')
        .appendField('Clim')
        .appendField(newblockly.FieldTextInput(''), 'cLimMin')
        .appendField(newblockly.FieldTextInput(''), 'cLimMax');
        this.appendDummyInput('cBarLabel')
        .appendField('Cbarlabel')
        .appendField(newblockly.FieldTextInput(''), 'cBarLabel');
        this.appendDummyInput('cBarDirection')
        .appendField('Cbardirection')
        .appendField(newblockly.FieldDropdown([
            ['none', 'none'],
            ['Horizontal', 'horizontal'],
            ['Vertical', 'vertical']
            ]), 'cBarDirection');
        this.setOutput(true, null);
        this.setTooltip('');
        this.setHelpUrl('');
        this.setColour(225);
    }
};
Blockly.common.defineBlocks({coloring: coloring});
