        test_xml = """
        <application xmlns="http://www.zetcom.com/ria/ws/module">
            <modules>
                <module name="Object">
                    <moduleItem>
                        <dataField name="ObjTechnicalTermClb">
                          <value>Dia, Farbe</value>
                        </dataField>
                        <dataField name="ObjObjectNumberSortedTxt">
                          <value>0008 B 022003</value>
                        </dataField>
                        <vocabularyReference name="ObjCategoryVoc">
                          <vocabularyReferenceItem id="3206624"/>
                        </vocabularyReference>
                        <vocabularyReference name="ObjNormalLocationVoc">
                          <vocabularyReferenceItem id="4216877"/>
                        </vocabularyReference>
                        <vocabularyReference name="ObjPublicationStatusVoc">
                          <vocabularyReferenceItem id="4399323"/>
                        </vocabularyReference>
                        <vocabularyReference name="ObjOrgGroupVoc">
                          <vocabularyReferenceItem id="1632808"/>
                        </vocabularyReference>
                        <repeatableGroup name="ObjGeograficGrp">
                          <repeatableGroupItem id="52002245">
                            <dataField name="SortLnu">
                              <value>5</value>
                            </dataField>
                            <vocabularyReference name="GeopolVoc">
                              <vocabularyReferenceItem id="4399065"/>
                            </vocabularyReference>
                            <vocabularyReference name="PlaceVoc">
                              <vocabularyReferenceItem id="2283566"/>
                            </vocabularyReference>
                          </repeatableGroupItem>
                        </repeatableGroup>
                        <repeatableGroup name="ObjDimAllGrp">
                          <repeatableGroupItem id="52002260">
                            <dataField name="SortLnu">
                              <value>2</value>
                            </dataField>
                            <dataField name="HeightNum">
                              <value>24</value>
                            </dataField>
                            <dataField name="WidthNum">
                              <value>36</value>
                            </dataField>
                            <vocabularyReference name="UnitDdiVoc">
                              <vocabularyReferenceItem id="3582020"/>
                            </vocabularyReference>
                            <moduleReference name="TypeDimRef">
                              <moduleReferenceItem moduleItemId="30"/>
                            </moduleReference>
                          </repeatableGroupItem>
                        </repeatableGroup>
                        <repeatableGroup name="ObjAcquisitionDateGrp">
                          <repeatableGroupItem id="52002264">
                            <dataField name="DateFromTxt">
                              <value>10.02.2016</value>
                            </dataField>
                            <dataField name="SortLnu">
                              <value>1</value>
                            </dataField>
                          </repeatableGroupItem>
                        </repeatableGroup>
                        <repeatableGroup name="ObjAcquisitionMethodGrp">
                          <repeatableGroupItem id="52002262">
                            <vocabularyReference name="MethodVoc">
                              <vocabularyReferenceItem id="1630994"/>
                            </vocabularyReference>
                          </repeatableGroupItem>
                        </repeatableGroup>
                        <repeatableGroup name="ObjPublicationGrp">
                          <repeatableGroupItem id="52002250">
                            <dataField name="SortLnu">
                              <value>1</value>
                            </dataField>
                            <vocabularyReference name="PublicationVoc">
                              <vocabularyReferenceItem id="4491690"/>
                            </vocabularyReference>
                            <vocabularyReference name="TypeVoc">
                              <vocabularyReferenceItem id="2600647"/>
                            </vocabularyReference>
                          </repeatableGroupItem>
                        </repeatableGroup>
                        <repeatableGroup name="ObjTechnicalTermGrp">
                          <repeatableGroupItem id="52002255">
                            <dataField name="TechnicalTermMultipleBoo">
                              <value>false</value>
                            </dataField>
                            <dataField name="SortLnu">
                              <value>1</value>
                            </dataField>
                            <vocabularyReference name="TechnicalTermVoc">
                              <vocabularyReferenceItem id="4288804"/>
                            </vocabularyReference>
                          </repeatableGroupItem>
                        </repeatableGroup>
                        <repeatableGroup name="ObjDateGrp">
                          <repeatableGroupItem id="52002249">
                            <dataField name="DateTxt">
                              <value>1985</value>
                            </dataField>
                            <dataField name="PreviewOther1Txt">
                              <value>01.01.1980–31.12.1980</value>
                            </dataField>
                            <dataField name="PreviewOther2Txt">
                              <value>01.01.1980–31.12.1980</value>
                            </dataField>
                            <dataField name="PreviewTxt">
                              <value>01.01.1980–31.12.1980</value>
                            </dataField>
                            <dataField name="DateFromTxt">
                              <value>01.01.1985</value>
                            </dataField>
                            <dataField name="DateToTxt">
                              <value>31.12.1985</value>
                            </dataField>
                            <dataField name="SortLnu">
                              <value>1</value>
                            </dataField>
                          </repeatableGroupItem>
                        </repeatableGroup>
                        <moduleReference name="ObjOwnerRef">
                          <moduleReferenceItem moduleItemId="67678"/>
                        </moduleReference>
                        <moduleReference name="ObjPerAssociationRef">
                          <moduleReferenceItem moduleItemId="401935">
                            <dataField name="SortLnu">
                              <value>1</value>
                            </dataField>
                            <vocabularyReference name="RoleVoc">
                              <vocabularyReferenceItem id="4378324"/>
                            </vocabularyReference>
                          </moduleReferenceItem>
                          <moduleReferenceItem moduleItemId="401935">
                            <dataField name="SortLnu">
                              <value>5</value>
                            </dataField>
                            <vocabularyReference name="RoleVoc">
                              <vocabularyReferenceItem id="4378452"/>
                            </vocabularyReference>
                          </moduleReferenceItem>
                          <moduleReferenceItem moduleItemId="402082">
                            <dataField name="SortLnu">
                              <value>10</value>
                            </dataField>
                            <vocabularyReference name="RoleVoc">
                              <vocabularyReferenceItem id="4378452"/>
                            </vocabularyReference>
                          </moduleReferenceItem>
                        </moduleReference>
                        <composite name="ObjObjectCre">
                          <compositeItem>
                            <moduleReference name="ObjObjectARef">
                              <moduleReferenceItem moduleItemId="2230815">
                                <vocabularyReference name="TypeAVoc">
                                  <vocabularyReferenceItem id="4399771"/>
                                </vocabularyReference>
                                <vocabularyReference name="TypeBVoc">
                                  <vocabularyReferenceItem id="4399773"/>
                                </vocabularyReference>
                                <vocabularyReference name="PreselectTypeAVoc">
                                  <vocabularyReferenceItem id="4399773"/>
                                </vocabularyReference>
                                <vocabularyReference name="PreselectTypeBVoc">
                                  <vocabularyReferenceItem id="4399771"/>
                                </vocabularyReference>
                              </moduleReferenceItem>
                              <moduleReferenceItem moduleItemId="2338384">
                                <vocabularyReference name="TypeBVoc">
                                  <vocabularyReferenceItem id="4399771"/>
                                </vocabularyReference>
                                <vocabularyReference name="PreselectTypeAVoc">
                                  <vocabularyReferenceItem id="4399771"/>
                                </vocabularyReference>
                              </moduleReferenceItem>
                            </moduleReference>
                          </compositeItem>
                        </composite>
                    </moduleItem>
                </module>
            </modules>
        </application>
        """
        testM = Module(xml=test_xml)
